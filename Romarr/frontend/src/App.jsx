import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import Library from './views/Library';
import AddNew from './views/Add';

// Functional Wanted ROMs View
const Wanted = () => {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/games?limit=100')
      .then(res => res.json())
      .then(data => {
        setGames(data.filter(g => g.requested_status && g.requested_status !== 'completed'));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="content-wrapper">
      <div style={{ marginBottom: '20px' }}>
        <h2>Wanted ROMs</h2>
        <p style={{ color: 'var(--text-secondary)' }}>Games currently being searched or downloaded.</p>
      </div>
      
      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center' }}>Loading pending requests...</div>
      ) : (
        games.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {games.map(game => (
              <div key={game.id} className="card" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{game.title}</h3>
                  <div style={{ display: 'flex', gap: '15px', marginTop: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    <span>Platform: {game.platform_name}</span>
                    <span>Status: <b style={{ color: 'var(--primary-color)', textTransform: 'uppercase' }}>{game.requested_status}</b></span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button className="btn" style={{ fontSize: '0.8rem' }}>Check Status</button>
                  <button className="btn" style={{ fontSize: '0.8rem', borderColor: 'var(--danger-color)', color: 'var(--danger-color)' }}>Cancel</button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p>Your wanted list is empty. Start by adding a game from the search catalog.</p>
          </div>
        )
      )}
    </div>
  );
};

// Functional Activity View
const ActivityView = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchActivity = () => {
      fetch('/api/activity')
        .then(res => res.ok ? res.json() : [])
        .then(data => {
          setActivities(Array.isArray(data) ? data : []);
          setLoading(false);
        })
        .catch(() => {
          setActivities([]);
          setLoading(false);
        });
    };

    fetchActivity();
    const interval = setInterval(fetchActivity, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="content-wrapper">
      <div style={{ marginBottom: '20px' }}>
        <h2>System Activity</h2>
        <p style={{ color: 'var(--text-secondary)' }}>Real-time background tasks and download progress.</p>
      </div>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center' }}>Connecting to system tasks...</div>
      ) : (
        activities.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {activities.map(a => (
              <div key={a.id} className="card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', alignItems: 'center' }}>
                  <h4 style={{ margin: 0 }}>{a.name}</h4>
                  <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: 'var(--primary-color)' }}>{a.progress}%</span>
                </div>
                <div style={{ height: '8px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div 
                    style={{ 
                      height: '100%', 
                      width: `${a.progress}%`, 
                      backgroundColor: 'var(--primary-color)', 
                      transition: 'width 0.5s ease',
                      boxShadow: '0 0 10px var(--primary-color)'
                    }} 
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p>No active background activity. System is idling.</p>
          </div>
        )
      )}
    </div>
  );
};

const Settings = () => {
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState('general');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch('/api/settings')
      .then(res => res.json())
      .then(data => setSettings(data));
  }, []);

  const handleTestConnection = async (type) => {
    let payload = {};
    let endpoint = "";
    
    if (type === 'prowlarr') {
      endpoint = "/api/admin/test/prowlarr";
      payload = { url: settings.indexers.prowlarr_url, api_key: settings.indexers.prowlarr_api_key };
    } else if (type === 'qbittorrent') {
      endpoint = "/api/admin/test/qbittorrent";
      payload = { 
        url: settings.downloaders.qbittorrent_url, 
        user: settings.downloaders.qbittorrent_user, 
        pass: settings.downloaders.qbittorrent_pass 
      };
    } else if (type === 'rawg') {
      endpoint = "/api/admin/test/rawg";
      payload = { api_key: settings.metadata?.rawg_api_key };
    }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      alert(data.message);
    } catch (err) {
      alert(`Test failed: ${err.message}`);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      alert("Settings saved!");
    } catch (err) {
      alert("Error saving settings");
    } finally {
      setSaving(false);
    }
  };

  if (!settings) return <div className="content-wrapper">Loading settings...</div>;

  return (
    <div className="content-wrapper">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Settings</h2>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div style={{ display: 'flex', gap: '20px', marginBottom: '30px', borderBottom: '1px solid var(--border-color)' }}>
        {['general', 'ui', 'media', 'metadata', 'indexers', 'downloaders'].map(tab => (
          <button 
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{ 
              padding: '10px 20px', 
              background: 'none', 
              border: 'none', 
              color: activeTab === tab ? 'var(--primary-color)' : 'var(--text-secondary)',
              borderBottom: activeTab === tab ? '2px solid var(--primary-color)' : 'none',
              cursor: 'pointer',
              textTransform: 'capitalize'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="card" style={{ maxWidth: '800px' }}>
        {activeTab === 'general' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3>General & Security</h3>
            <div>
              <label style={{ display: 'block', marginBottom: '8px' }}>API Key</label>
              <div style={{ display: 'flex', gap: '10px' }}>
                <input type="text" value={settings.security.api_key} readOnly style={{ flexGrow: 1 }} />
                <button className="btn" onClick={() => {
                  const newKey = Math.random().toString(36).substring(2, 15);
                  setSettings({...settings, security: {...settings.security, api_key: newKey}});
                }}>Generate</button>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <input 
                type="checkbox" 
                checked={settings.security.auth_enabled} 
                onChange={e => setSettings({...settings, security: {...settings.security, auth_enabled: e.target.checked}})} 
              />
              <label>Enable Authentication</label>
            </div>
          </div>
        )}

        {activeTab === 'ui' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3>UI Customization</h3>
            <div>
              <label style={{ display: 'block', marginBottom: '8px' }}>Language</label>
              <select 
                value={settings.ui.language} 
                onChange={e => setSettings({...settings, ui: {...settings.ui, language: e.target.value}})}
                style={{ width: '100%' }}
              >
                <option value="en-US">English (US)</option>
                <option value="es-ES">Spanish</option>
                <option value="fr-FR">French</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px' }}>Date Format</label>
              <input 
                type="text" 
                value={settings.ui.date_format} 
                onChange={e => setSettings({...settings, ui: {...settings.ui, date_format: e.target.value}})}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        )}

        {activeTab === 'media' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3>Media Management</h3>
            <div>
              <label style={{ display: 'block', marginBottom: '8px' }}>Naming Convention</label>
              <input 
                type="text" 
                value={settings.media.naming_convention} 
                onChange={e => setSettings({...settings, media: {...settings.media, naming_convention: e.target.value}})}
                style={{ width: '100%' }}
                placeholder="{Platform}/{Title} ({Year})"
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px' }}>Permissions (CHMOD)</label>
              <input 
                type="text" 
                value={settings.media.chmod} 
                onChange={e => setSettings({...settings, media: {...settings.media, chmod: e.target.value}})}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        )}

        {activeTab === 'metadata' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3>External Metadata (RAWG)</h3>
              <button className="btn" onClick={() => handleTestConnection('rawg')}>Test RAWG Connection</button>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px' }}>RAWG API Key</label>
              <input 
                type="password" 
                value={settings.metadata?.rawg_api_key || ''} 
                onChange={e => setSettings({...settings, metadata: {...(settings.metadata || {}), rawg_api_key: e.target.value}})}
                style={{ width: '100%' }}
                placeholder="Enter your RAWG.io API key"
              />
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
                Get a free key at <a href="https://rawg.io/apidocs" target="_blank" rel="noreferrer" style={{ color: 'var(--primary-color)' }}>rawg.io/apidocs</a>
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <input 
                type="checkbox" 
                checked={settings.metadata?.prefer_external_data || false} 
                onChange={e => setSettings({...settings, metadata: {...(settings.metadata || {}), prefer_external_data: e.target.checked}})} 
              />
              <label>Prefer External Metadata (Descriptions, Ratings)</label>
            </div>
          </div>
        )}

        {activeTab === 'indexers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3>Prowlarr Configuration</h3>
              <button className="btn" onClick={() => handleTestConnection('prowlarr')}>Test Connection</button>
            </div>
            <input 
              type="text" 
              placeholder="Prowlarr URL" 
              value={settings.indexers.prowlarr_url}
              onChange={e => setSettings({...settings, indexers: {...settings.indexers, prowlarr_url: e.target.value}})}
            />
            <input 
              type="password" 
              placeholder="API Key" 
              value={settings.indexers.prowlarr_api_key}
              onChange={e => setSettings({...settings, indexers: {...settings.indexers, prowlarr_api_key: e.target.value}})}
            />
          </div>
        )}

        {activeTab === 'downloaders' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3>qBittorrent Configuration</h3>
              <button className="btn" onClick={() => handleTestConnection('qbittorrent')}>Test Connection</button>
            </div>
            <input 
              type="text" 
              placeholder="qBittorrent URL" 
              value={settings.downloaders.qbittorrent_url}
              onChange={e => setSettings({...settings, downloaders: {...settings.downloaders, qbittorrent_url: e.target.value}})}
            />
            <input 
              type="text" 
              placeholder="Username" 
              value={settings.downloaders.qbittorrent_user}
              onChange={e => setSettings({...settings, downloaders: {...settings.downloaders, qbittorrent_user: e.target.value}})}
            />
            <input 
              type="password" 
              placeholder="Password" 
              value={settings.downloaders.qbittorrent_pass}
              onChange={e => setSettings({...settings, downloaders: {...settings.downloaders, qbittorrent_pass: e.target.value}})}
            />
          </div>
        )}
      </div>
    </div>
  );
};

function App() {
  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Navbar title="Romarr" />
          <Routes>
            <Route path="/" element={<Library />} />
            <Route path="/add" element={<AddNew />} />
            <Route path="/wanted" element={<Wanted />} />
            <Route path="/activity" element={<ActivityView />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
