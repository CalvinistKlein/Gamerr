import React, { useState, useEffect } from 'react';
import { LayoutGrid, List, Filter, Download, Info, CheckCircle2, Search, Trash2, CheckSquare, Square, RefreshCw } from 'lucide-react';

const GameImage = ({ src, title, style, platform }) => {
  const [error, setError] = useState(false);

  if (!src || error) {
    return (
      <div style={{
        ...style,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1a1a1a 0%, #000 100%)',
        color: '#fff',
        padding: '15px',
        textAlign: 'center',
        border: '1px solid rgba(255,255,255,0.05)',
        boxShadow: 'inset 0 0 40px rgba(0,0,0,0.8)'
      }}>
        <div style={{ fontSize: '0.65rem', fontWeight: 'bold', marginBottom: '8px', opacity: 0.4, textTransform: 'uppercase', letterSpacing: '1px' }}>{platform || 'ROM'}</div>
        <div style={{ fontSize: '0.9rem', fontWeight: '500', wordBreak: 'break-word', marginBottom: '20px' }}>{title}</div>
        <div style={{ marginTop: 'auto', fontSize: '0.6rem', opacity: 0.3, letterSpacing: '2px' }}>IMAGE NOT FOUND</div>
      </div>
    );
  }

  return (
    <img 
      src={src} 
      alt={title} 
      onError={() => setError(true)}
      style={{ ...style, objectFit: 'cover' }} 
    />
  );
};

const Library = () => {
  const [viewMode, setViewMode] = useState('grid');
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedGame, setSelectedGame] = useState(null);
  const [platformFilter, setPlatformFilter] = useState('All Platforms');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());
  
  const toggleSelection = (e, id) => {
    e.stopPropagation();
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const deleteSelected = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedIds.size} selected games?`)) return;

    try {
      const res = await fetch('/api/games/batch', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_ids: Array.from(selectedIds) })
      });
      if (res.ok) {
        setGames(prev => prev.filter(g => !selectedIds.has(g.id)));
        setSelectedIds(new Set());
      } else {
        alert("Deletion failed");
      }
    } catch (err) {
      console.error(err);
      alert("Error deleting games");
    }
  };

  const deleteSingleGame = async (gameId) => {
    if (!confirm("Are you sure you want to delete this game?")) return;

    try {
      const res = await fetch('/api/games/batch', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_ids: [gameId] })
      });
      if (res.ok) {
        setGames(prev => prev.filter(g => g.id !== gameId));
        setSelectedGame(null);
      } else {
        alert("Deletion failed");
      }
    } catch (err) {
      console.error(err);
      alert("Error deleting game");
    }
  };

  useEffect(() => {
    fetch('/api/games?limit=100')
      .then(res => res.json())
      .then(data => {
        setGames(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error fetching games:", err);
        setLoading(false);
      });
  }, []);

  const filteredGames = games.filter(g => {
    const matchesPlatform = platformFilter === 'All Platforms' || g.platform_name === platformFilter;
    const matchesSearch = g.title.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesPlatform && matchesSearch;
  });

  const platforms = ['All Platforms', ...new Set(games.map(g => g.platform_name).filter(Boolean))];

  if (loading) {
    return (
      <div className="content-wrapper" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <div className="loader"></div>
        <span style={{ marginLeft: '15px', color: 'var(--text-secondary)' }}>Loading your library...</span>
      </div>
    );
  }

  return (
    <div className="content-wrapper">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '10px', marginRight: '10px' }}>
            <button className="btn" style={{ background: viewMode === 'grid' ? 'rgba(39, 174, 96, 0.1)' : 'transparent', borderColor: viewMode === 'grid' ? 'var(--primary-color)' : 'var(--border-color)' }} onClick={() => setViewMode('grid')}>
              <LayoutGrid size={18} color={viewMode === 'grid' ? 'var(--primary-color)' : 'currentColor'} />
            </button>
            <button className="btn" style={{ background: viewMode === 'list' ? 'rgba(39, 174, 96, 0.1)' : 'transparent', borderColor: viewMode === 'list' ? 'var(--primary-color)' : 'var(--border-color)' }} onClick={() => setViewMode('list')}>
              <List size={18} color={viewMode === 'list' ? 'var(--primary-color)' : 'currentColor'} />
            </button>
          </div>
          
          {selectedIds.size > 0 && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '15px', 
              padding: '8px 15px', 
              backgroundColor: 'rgba(231, 76, 60, 0.1)', 
              border: '1px solid var(--danger-color)',
              borderRadius: '6px',
              animation: 'fadeIn 0.2s ease'
            }}>
              <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: 'var(--danger-color)' }}>{selectedIds.size} Selected</span>
              <button 
                className="btn" 
                style={{ height: '30px', padding: '0 10px', fontSize: '0.8rem', borderColor: 'var(--danger-color)', color: 'var(--danger-color)' }}
                onClick={deleteSelected}
              >
                <Trash2 size={14} style={{ marginRight: '5px' }} /> Delete
              </button>
              <button 
                className="btn" 
                style={{ height: '30px', padding: '0 10px', fontSize: '0.8rem' }}
                onClick={() => setSelectedIds(new Set())}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
            <input 
              type="text" 
              placeholder="Search library..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '35px', width: '250px' }} 
            />
          </div>
          <select 
            style={{ width: '180px' }} 
            value={platformFilter} 
            onChange={(e) => setPlatformFilter(e.target.value)}
          >
            {platforms.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <button className="btn btn-primary">
            <Filter size={18} /> Apply Filter
          </button>
        </div>
      </div>

      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: viewMode === 'grid' ? 'repeat(auto-fill, minmax(200px, 1fr))' : '1fr', 
        gap: '24px' 
      }}>
        {filteredGames.map(game => (
          <div 
            key={game.id} 
            className="card game-card-hover" 
            onClick={() => setSelectedGame(game)}
            style={{ 
              padding: 0, 
              overflow: 'hidden', 
              position: 'relative', 
              display: 'flex', 
              flexDirection: viewMode === 'grid' ? 'column' : 'row',
              cursor: 'pointer',
              transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
              height: viewMode === 'list' ? '80px' : 'auto'
            }}
          >
            <div style={{ 
              height: viewMode === 'grid' ? '280px' : '80px', 
              width: viewMode === 'grid' ? '100%' : '60px',
              position: 'relative', 
              backgroundColor: '#444',
              flexShrink: 0
            }}>
              <GameImage 
                src={game.cover_url} 
                title={game.title}
                platform={game.platform_name}
                style={{ width: '100%', height: '100%' }} 
              />
              <div 
                onClick={(e) => toggleSelection(e, game.id)}
                style={{ 
                  position: 'absolute', 
                  top: '10px', 
                  left: '10px',
                  zIndex: 2,
                  color: selectedIds.has(game.id) ? 'var(--primary-color)' : '#fff',
                  cursor: 'pointer',
                  filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.5))'
                }}
              >
                {selectedIds.has(game.id) ? <CheckSquare size={20} /> : <Square size={20} />}
              </div>
              {viewMode === 'grid' && (
                <div style={{ 
                  position: 'absolute', 
                  top: '10px', 
                  right: '10px',
                  backgroundColor: 'rgba(0,0,0,0.8)',
                  backdropFilter: 'blur(4px)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  border: '1px solid var(--border-color)',
                  color: '#fff'
                }}>
                  {game.platform_name || 'PC'}
                </div>
              )}
            </div>
            
            <div style={{ padding: '12px', flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <h3 style={{ fontSize: '1rem', marginBottom: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{game.title}</h3>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{game.release_year || 'Unknown'}</span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <Info size={16} style={{ color: 'var(--text-secondary)' }} />
                  {game.status === 'Completed' ? (
                    <CheckCircle2 size={16} style={{ color: 'var(--success-color)' }} />
                  ) : (
                    <Download size={16} style={{ color: 'var(--text-secondary)' }} />
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Game Details Modal */}
      {selectedGame && (
        <div style={{ 
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          backgroundColor: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)',
          display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 10000 
        }} onClick={() => setSelectedGame(null)}>
          <div className="card" style={{ maxWidth: '800px', width: '90%', display: 'flex', gap: '30px', padding: '30px', position: 'relative' }} onClick={e => e.stopPropagation()}>
            <button 
              onClick={() => setSelectedGame(null)}
              style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
            >
              <Info size={24} style={{ transform: 'rotate(45deg)' }} />
            </button>
            <GameImage 
              src={selectedGame.cover_url} 
              title={selectedGame.title}
              platform={selectedGame.platform_name}
              style={{ width: '250px', height: '375px', borderRadius: '8px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)', flexShrink: 0 }} 
            />
            <div style={{ flexGrow: 1 }}>
              <span style={{ color: 'var(--primary-color)', fontSize: '0.9rem', fontWeight: 'bold', textTransform: 'uppercase' }}>{selectedGame.platform_name}</span>
              <h2 style={{ fontSize: '2rem', margin: '10px 0' }}>{selectedGame.title}</h2>
              <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                <span>{selectedGame.release_year}</span>
                <span>Rating: {selectedGame.rating || 'N/A'}%</span>
              </div>
              <p style={{ lineHeight: '1.6', color: 'var(--text-main)', marginBottom: '30px' }}>
                {selectedGame.summary || "No description available for this title."}
              </p>
              <div style={{ display: 'flex', gap: '15px' }}>
                <button className="btn btn-primary" style={{ flexGrow: 1, justifyContent: 'center', padding: '12px' }}>Download ROM</button>
                <button 
                  className="btn" 
                  style={{ flexGrow: 1, justifyContent: 'center', padding: '12px' }}
                  onClick={async () => {
                    const btn = document.activeElement;
                    btn.innerText = "Refreshing...";
                    try {
                      const res = await fetch(`/api/games/${selectedGame.id}/refresh-metadata`, { method: 'POST' });
                      if (res.ok) {
                        const updated = await fetch(`/api/games/${selectedGame.id}`);
                        const newData = await updated.json();
                        setSelectedGame(newData);
                        setGames(prev => prev.map(g => g.id === newData.id ? newData : g));
                        alert("Metadata updated!");
                      } else {
                        alert("Refresh failed. Check API key.");
                      }
                    } catch (err) {
                      alert("Network error");
                    } finally {
                      btn.innerText = "Refresh Metadata";
                    }
                  }}
                >
                  <RefreshCw size={18} style={{ marginRight: '8px' }} /> Refresh Metadata
                </button>
                <button 
                  className="btn" 
                  style={{ flexGrow: 1, justifyContent: 'center', padding: '12px', borderColor: 'var(--danger-color)', color: 'var(--danger-color)' }}
                  onClick={() => deleteSingleGame(selectedGame.id)}
                >
                  <Trash2 size={18} style={{ marginRight: '8px' }} /> Delete ROM
                </button>
                <button className="btn" style={{ flexGrow: 1, justifyContent: 'center', padding: '12px' }}>Edit Metadata</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Library;
