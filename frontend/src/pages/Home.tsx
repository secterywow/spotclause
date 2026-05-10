export default function Home() {
  return (
    <div className="page home-page">
      <div className="upload-zone">
        <div className="upload-icon">📄 📁 📎</div>
        <h2>Select Contract File</h2>
        <p>Support PDF, Word, Image formats</p>
        <p className="text-muted">Max 20MB</p>
        <div className="divider">or</div>
        <button className="btn btn-secondary">Paste Contract Text</button>
        <p className="privacy-note">
          ⚠️ Your contract data is only used for analysis and will not be saved.
        </p>
      </div>
    </div>
  )
}
