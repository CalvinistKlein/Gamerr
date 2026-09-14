import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Upload, X, CheckCircle, AlertCircle, Database } from 'lucide-react';

const AddNew = () => {
  const [activeTab, setActiveTab] = useState('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  
  const [romFiles, setRomFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const [dbFile, setDbFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const [searchParams, setSearchParams] = useSearchParams();
  const [ingestionProgress, setIngestionProgress] = useState(null);

  useEffect(() => {
    const q = searchParams.get('search');
    if (q) {
      setActiveTab('search');
      setSearchQuery(q);
      executeSearch(q);
    }
  }, [searchParams]);

  useEffect(() => {
    let interval;
    if (importing) {
      interval = setInterval(async () => {
        try {
          const res = await fetch('/api/admin/progress');
          const data = await res.json();
          setIngestionProgress(data);
          if (data.status === 'idle') {
            clearInterval(interval);
            setImporting(false);
          }
        } catch (e) {
          console.error("Progress fetch failed", e);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [importing]);

  const executeSearch = async (query) => {
    setSearching(true);
    try {
      const response = await fetch(`/api/games?query=${encodeURIComponent(query)}&limit=10&all=true`);
      const data = await response.json();
      setSearchResults(data);
    } catch (err) {
      console.error(err);
    } finally {
      setSearching(false);
    }
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e, type) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    if (type === 'roms') {
      setRomFiles(prev => [...prev, ...files]);
    } else if (type === 'database') {
      const file = files[0];
      setDbFile(file);
      // Construct a faux event to reuse handleDbAnalyze
      handleDbAnalyze({ target: { files: [file] } });
    }
  };

  // --- Search Logic ---
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery) return;
    executeSearch(searchQuery);
  };

  const [requestingIds, setRequestingIds] = useState(new Set());

  const handleRequest = async (gameId) => {
    setRequestingIds(prev => new Set(prev).add(gameId));
    try {
      const resp = await fetch('/api/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId })
      });
      if (resp.ok) {
        setSearchResults(prev => prev.map(g => g.id === gameId ? {...g, requested_status: 'searching'} : g));
      }
    } catch (err) {
      alert("Request failed");
    } finally {
      setRequestingIds(prev => {
        const next = new Set(prev);
        next.delete(gameId);
        return next;
      });
    }
  };

  // --- ROM Upload Logic ---
  const handleRomUpload = () => {
    if (romFiles.length === 0) return;
    setUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    romFiles.forEach(f => formData.append('files[]', f));

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload/rom', true);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        setUploadProgress(percent);
      }
    };

    xhr.onload = () => {
      setUploading(false);
      if (xhr.status === 201) {
        alert("ROMs uploaded and organized successfully!");
        setRomFiles([]);
      } else {
        alert("Upload failed: " + xhr.responseText);
      }
    };

    xhr.onerror = () => {
      setUploading(false);
      alert("Upload failed due to network error.");
    };

    xhr.send(formData);
  };

  // --- Database Analysis Logic ---
  const handleDbAnalyze = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setDbFile(file);
    setAnalyzing(true);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/admin/backup/analyze', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      alert("Analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDbApply = async () => {
    if (!analysis) return;
    setImporting(true);
    try {
      const response = await fetch('/api/admin/backup/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(analysis)
      });
      if (response.ok) {
        alert("Import successful! Refreshing...");
        window.location.reload();
      }
    } catch (err) {
      alert("Import failed.");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="content-wrapper">
      <div style={{ display: 'flex', gap: '30px', marginBottom: '30px', borderBottom: '1px solid var(--border-color)' }}>
        {['search', 'roms', 'database'].map(tab => (
          <button 
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{ 
              padding: '12px 24px', 
              background: 'none', 
              border: 'none', 
              color: activeTab === tab ? 'var(--primary-color)' : 'var(--text-secondary)',
              borderBottom: activeTab === tab ? '2px solid var(--primary-color)' : 'none',
              cursor: 'pointer',
              fontWeight: activeTab === tab ? '600' : '400',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              fontSize: '0.9rem'
            }}
          >
            {tab === 'roms' ? 'Upload ROMs' : tab === 'database' ? 'Import Database' : 'Search Games'}
          </button>
        ))}
      </div>

      <div className="card" style={{ maxWidth: '900px' }}>
        {activeTab === 'search' && (
          <div>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
              <input 
                type="text" 
                placeholder="Search global game catalog..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ flexGrow: 1 }}
              />
              <button className="btn btn-primary" type="submit" disabled={searching}>
                {searching ? 'Searching...' : 'Search'}
              </button>
            </form>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {searchResults.map(game => {
                const isRequested = game.requested_status || requestingIds.has(game.id);
                return (
                  <div key={game.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
                    <div>
                      <h4 style={{ margin: '0 0 4px 0' }}>{game.title}</h4>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{game.platform_name} • {game.release_year || 'Year Unknown'}</span>
                    </div>
                    <button 
                      className={`btn ${game.requested_status ? 'btn-secondary' : 'btn-primary'}`} 
                      onClick={() => handleRequest(game.id)} 
                      disabled={isRequested}
                      style={{ minWidth: '120px' }}
                    >
                      {requestingIds.has(game.id) ? 'Requesting...' : (game.requested_status ? game.requested_status.toUpperCase() : 'Request')}
                    </button>
                  </div>
                );
              })}
              {searchResults.length === 0 && !searching && <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '20px' }}>No games found. Try a different search.</p>}
            </div>
          </div>
        )}

        {activeTab === 'roms' && (
          <div>
            <h3>Multi-ROM Web Upload</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>Select multiple files to import directly into your existing library.</p>
            <div 
              className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
              onClick={() => document.getElementById('romInput').click()}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={(e) => onDrop(e, 'roms')}
              style={{ 
                padding: '60px', 
                border: '2px dashed',
                borderColor: isDragging ? 'var(--primary-color)' : 'var(--border-color)',
                backgroundColor: isDragging ? 'rgba(39, 174, 96, 0.05)' : 'transparent',
                borderRadius: '8px', 
                textAlign: 'center', 
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <Upload size={48} style={{ color: isDragging ? 'var(--primary-color)' : 'var(--text-secondary)', marginBottom: '16px' }} />
              <p>{isDragging ? 'Drop ROMs here' : 'Click to browse or drag ROM files here'}</p>
              <input id="romInput" type="file" multiple style={{ display: 'none' }} onChange={(e) => setRomFiles(Array.from(e.target.files))} />
            </div>
              <div style={{ marginTop: '20px' }}>
                <button 
                  className="btn btn-primary" 
                  style={{ width: '100%' }} 
                  disabled={uploading} 
                  onClick={handleRomUpload}
                >
                  {uploading ? `Uploading (${uploadProgress}%)...` : `Upload ${romFiles.length} Games`}
                </button>
                
                {uploading && (
                  <div style={{ marginTop: '15px', height: '10px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '5px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${uploadProgress}%`, backgroundColor: 'var(--primary-color)', transition: 'width 0.3s ease' }}></div>
                  </div>
                )}
              </div>
          </div>
        )}

        {activeTab === 'database' && (
          <div>
            <h3>Universal Database Import</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>Upload a ZIP, DAT, or ROMMAR file. The system will intelligently identify it.</p>
            
            <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'flex-end' }}>
              <button 
                onClick={async () => {
                  if (confirm("Reset current database? This will wipe all unsaved games!")) {
                    const res = await fetch('/api/admin/reset_db', { method: 'POST' });
                    if (res.ok) alert("Database reset to clean state.");
                    else alert("Reset failed.");
                  }
                }}
                style={{ fontSize: '0.8rem', color: 'var(--danger-color)', background: 'none', border: '1px solid var(--danger-color)', padding: '5px 10px', borderRadius: '4px', cursor: 'pointer' }}
              >
                Wipe & Start Fresh
              </button>
            </div>
            
            {!analysis ? (
              <div 
                className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
                onClick={() => document.getElementById('dbInput').click()}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={(e) => onDrop(e, 'database')}
                style={{ 
                  padding: '60px', 
                  border: '2px dashed',
                  borderColor: isDragging ? 'var(--primary-color)' : 'var(--border-color)',
                  backgroundColor: isDragging ? 'rgba(39, 174, 96, 0.05)' : 'transparent',
                  borderRadius: '8px', 
                  textAlign: 'center', 
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <Database size={48} style={{ color: isDragging ? 'var(--primary-color)' : 'var(--text-secondary)', marginBottom: '16px' }} />
                <p>{analyzing ? 'Analyzing File...' : (isDragging ? 'Drop database file here' : 'Upload Database File (.zip, .dat, .xml, .db)')}</p>
                <input id="dbInput" type="file" style={{ display: 'none' }} onChange={handleDbAnalyze} disabled={analyzing} />
              </div>
            ) : (
              <div className="card" style={{ backgroundColor: 'rgba(39, 174, 96, 0.05)', border: '1px solid var(--primary-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h4 style={{ margin: '0 0 10px 0', color: 'var(--primary-color)' }}>File Identified!</h4>
                    <p style={{ margin: '5px 0' }}><strong>Type:</strong> {analysis.type}</p>
                    {analysis.platform && <p style={{ margin: '5px 0' }}><strong>Platform:</strong> {analysis.platform}</p>}
                    <p style={{ margin: '5px 0', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>File: {analysis.filename}</p>
                  </div>
                  <X size={20} style={{ cursor: 'pointer' }} onClick={() => { setAnalysis(null); setDbFile(null); }} />
                </div>
                <button 
                  className="btn btn-primary" 
                  style={{ width: '100%', marginTop: '20px', justifyContent: 'center' }}
                  onClick={handleDbApply}
                  disabled={importing}
                >
                  {importing ? (ingestionProgress ? `Importing: ${ingestionProgress.progress}%` : 'Processing...') : 'Confirm Import / Restore'}
                </button>
                {importing && ingestionProgress && (
                  <div style={{ marginTop: '10px', fontSize: '0.85rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
                    {ingestionProgress.message}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AddNew;
