from celery import shared_task
from app.celery_app import celery_app
from app.logger import get_logger
from app.services.file_parser import parse_file_sync
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=2)
def analyze_contract(self, file_path: str, mime_type: str, user_id: int, contract_record_id: int):
    """Full contract analysis pipeline.

    Steps:
    1. Parse file → extract text
    2. Detect jurisdiction
    3. Identify contract type
    4. Structure clauses
    5. Match risk rules
    6. Analyze each clause (serial, streaming)
    7. Detect missing clauses
    8. Extract key terms
    9. Extract dates
    10. Assemble report
    """
    try:
        logger.info("Starting contract analysis",
                   contract_record_id=contract_record_id,
                   user_id=user_id)

        # Step 1: Parse file
        self.update_state(state='PROGRESS', meta={'step': 1, 'step_name': 'Parsing contract...'})
        parsed = parse_file_sync(file_path, mime_type)
        raw_text = parsed['text']

        if not raw_text or len(raw_text) < 50:
            raise ValueError("Could not extract sufficient text from file")

        # Step 2: Detect jurisdiction
        self.update_state(state='PROGRESS', meta={'step': 2, 'step_name': 'Identifying type & region...'})
        from app.services.analysis import detect_jurisdiction
        jurisdiction = detect_jurisdiction(raw_text)

        # Step 3: Identify contract type
        self.update_state(state='PROGRESS', meta={'step': 2, 'step_name': 'Identifying type & region...'})
        from app.services.analysis import identify_contract_type
        contract_type = identify_contract_type(raw_text)

        # Step 4: Structure clauses
        self.update_state(state='PROGRESS', meta={'step': 3, 'step_name': 'Structuring clauses...'})
        from app.services.analysis import structure_clauses
        clauses = structure_clauses(raw_text)

        # Step 5: Match risk rules
        self.update_state(state='PROGRESS', meta={'step': 3, 'step_name': 'Matching risk rules...'})
        from app.services.analysis import match_risk_rules
        matched_rules = match_risk_rules(clauses, contract_type)

        # Step 6: Analyze each clause (serial)
        analysis_results = []
        total_clauses = len(clauses)
        for i, clause in enumerate(clauses):
            self.update_state(
                state='PROGRESS',
                meta={'step': 3, 'step_name': f'Analyzing clause {i+1}/{total_clauses}...'}
            )
            from app.services.analysis import analyze_clause
            result = analyze_clause(clause, matched_rules.get(clause['id'], []), jurisdiction)
            analysis_results.append(result)

        # Step 7: Detect missing clauses
        self.update_state(state='PROGRESS', meta={'step': 3, 'step_name': 'Detecting missing clauses...'})
        from app.services.analysis import detect_missing_clauses
        missing_clauses = detect_missing_clauses(contract_type, clauses)

        # Step 8: Extract key terms
        self.update_state(state='PROGRESS', meta={'step': 3, 'step_name': 'Extracting key terms...'})
        from app.services.analysis import extract_key_terms
        key_terms = extract_key_terms(raw_text)

        # Step 9: Extract dates
        self.update_state(state='PROGRESS', meta={'step': 3, 'step_name': 'Extracting dates...'})
        from app.services.analysis import extract_dates
        key_dates = extract_dates(raw_text)

        # Step 10: Assemble report
        self.update_state(state='PROGRESS', meta={'step': 4, 'step_name': 'Generating report...'})
        from app.services.analysis import assemble_report
        report = assemble_report(
            contract_type=contract_type,
            jurisdiction=jurisdiction,
            clauses=clauses,
            analysis_results=analysis_results,
            missing_clauses=missing_clauses,
            key_terms=key_terms,
            key_dates=key_dates,
        )

        # Save report to database
        from app.database import SessionLocal
        from app.models.contract import ContractRecord
        db = SessionLocal()
        try:
            record = db.query(ContractRecord).filter(ContractRecord.id == contract_record_id).first()
            if record:
                record.contract_type = contract_type
                record.jurisdiction = jurisdiction
                record.overall_score = report['overallScore']
                record.high_risk_count = report['riskBreakdown']['high']
                record.medium_risk_count = report['riskBreakdown']['medium']
                record.low_risk_count = report['riskBreakdown']['low']
                record.report_json = str(report)
                db.commit()
        finally:
            db.close()

        # Clean up temp file
        import os
        if os.path.exists(file_path):
            os.remove(file_path)

        logger.info("Contract analysis completed",
                   contract_record_id=contract_record_id)

        return {
            'status': 'completed',
            'contract_record_id': contract_record_id,
            'report': report,
        }

    except Exception as exc:
        logger.error("Contract analysis failed",
                    error=str(exc),
                    contract_record_id=contract_record_id)
        self.retry(exc=exc, countdown=10)
