from celery import shared_task
from app.celery_app import celery_app
from app.logger import get_logger
from app.services.file_parser import parse_file_sync

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=2)
def compare_contracts(self, old_file_path: str, old_mime_type: str,
                      new_file_path: str, new_mime_type: str,
                      user_id: int, compare_record_id: int):
    """Contract comparison pipeline.

    Steps:
    1. Parse both files
    2. Diff alignment
    3. Analyze each change
    4. Detect hidden traps
    5. Assemble report
    """
    try:
        logger.info("Starting contract comparison",
                   compare_record_id=compare_record_id,
                   user_id=user_id)

        # Step 1: Parse files
        self.update_state(state='PROGRESS', meta={'step': 1, 'step_name': 'Parsing contracts...'})
        old_parsed = parse_file_sync(old_file_path, old_mime_type)
        new_parsed = parse_file_sync(new_file_path, new_mime_type)

        old_text = old_parsed['text']
        new_text = new_parsed['text']

        # Step 2: Diff alignment
        self.update_state(state='PROGRESS', meta={'step': 2, 'step_name': 'Aligning differences...'})
        from app.services.comparison import align_differences
        changes = align_differences(old_text, new_text)

        # Step 3: Analyze each change
        self.update_state(state='PROGRESS', meta={'step': 3, 'step_name': 'Analyzing changes...'})
        from app.services.comparison import analyze_change_risk
        for change in changes:
            analysis = analyze_change_risk(change)
            change.update(analysis)

        # Step 4: Detect hidden traps
        self.update_state(state='PROGRESS', meta={'step': 4, 'step_name': 'Detecting hidden traps...'})
        from app.services.comparison import detect_hidden_traps
        hidden_traps = detect_hidden_traps(changes)

        # Step 5: Assemble report
        self.update_state(state='PROGRESS', meta={'step': 5, 'step_name': 'Generating report...'})
        from app.services.comparison import assemble_compare_report
        report = assemble_compare_report(changes, hidden_traps)

        # Clean up temp files
        import os
        for path in [old_file_path, new_file_path]:
            if os.path.exists(path):
                os.remove(path)

        logger.info("Contract comparison completed",
                   compare_record_id=compare_record_id)

        return {
            'status': 'completed',
            'compare_record_id': compare_record_id,
            'report': report,
        }

    except Exception as exc:
        logger.error("Contract comparison failed",
                    error=str(exc),
                    compare_record_id=compare_record_id)
        self.retry(exc=exc, countdown=10)
