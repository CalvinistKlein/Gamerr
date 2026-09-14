import React, { useState, useEffect } from 'react';
import { Bell, Search, Activity, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Navbar = ({ title }) => {
  const navigate = useNavigate();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [activities, setActivities] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    // Fetch notifications if endpoint exists
    fetch('/api/notifications')
      .then(res => res.ok ? res.json() : [])
      .then(data => setNotifications(Array.isArray(data) ? data : []))
      .catch(() => setNotifications([]));

    // Fetch activities if endpoint exists
    const fetchActivity = () => {
      fetch('/api/activity')
        .then(res => res.ok ? res.json() : [])
        .then(data => setActivities(Array.isArray(data) ? data : []))
        .catch(() => setActivities([]));
    };

    fetchActivity();
    const interval = setInterval(fetchActivity, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = (e) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      navigate(`/add?search=${encodeURIComponent(searchQuery)}`);
      setSearchQuery('');
    }
  };

  return (
    <header className="top-nav">
      <div style={{ flexGrow: 1 }}>
        <h1 style={{ fontSize: '1.2rem', margin: 0 }}>{title}</h1>
      </div>
      <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
        <div style={{ position: 'relative' }}>
          <Search size={18} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
          <input 
            type="text" 
            placeholder="Search global catalog..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearch}
            style={{ paddingLeft: '35px', width: '250px', fontSize: '0.9rem' }} 
          />
        </div>
        
        {/* Notifications */}
        <div style={{ position: 'relative' }}>
          <Bell 
            size={20} 
            style={{ cursor: 'pointer', color: showNotifications ? 'var(--primary-color)' : 'var(--text-secondary)' }} 
            onClick={() => { setShowNotifications(!showNotifications); setShowActivity(false); setShowProfile(false); }}
          />
          {showNotifications && (
            <div className="card" style={{ position: 'absolute', top: '40px', right: 0, width: '300px', zIndex: 1000, padding: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h4 style={{ margin: 0 }}>Notifications</h4>
                {notifications.length > 0 && <span style={{ fontSize: '0.7rem', cursor: 'pointer', color: 'var(--primary-color)' }} onClick={() => setNotifications([])}>Clear All</span>}
              </div>
              {notifications.length > 0 ? notifications.map(n => (
                <div key={n.id} style={{ padding: '8px 0', borderBottom: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                  <div style={{ color: 'var(--text-main)' }}>{n.text}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{n.time}</div>
                </div>
              )) : (
                <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No new notifications</div>
              )}
            </div>
          )}
        </div>

        {/* Activity */}
        <div style={{ position: 'relative' }}>
          <Activity 
            size={20} 
            style={{ cursor: 'pointer', color: showActivity ? 'var(--primary-color)' : 'var(--text-secondary)' }} 
            onClick={() => { setShowActivity(!showActivity); setShowNotifications(false); setShowProfile(false); }}
          />
          {showActivity && (
            <div className="card" style={{ position: 'absolute', top: '40px', right: 0, width: '300px', zIndex: 1000, padding: '10px' }}>
              <h4 style={{ margin: '0 0 10px 0' }}>System Activity</h4>
              {activities.length > 0 ? activities.map(a => (
                <div key={a.id} style={{ padding: '8px 0', borderBottom: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span>{a.name}</span>
                    <span>{a.progress}%</span>
                  </div>
                  <div style={{ height: '4px', backgroundColor: 'var(--border-color)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${a.progress}%`, backgroundColor: 'var(--primary-color)' }} />
                  </div>
                </div>
              )) : (
                <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No active activity</div>
              )}
            </div>
          )}
        </div>

        {/* Profile */}
        <div style={{ position: 'relative' }}>
          <div 
            onClick={() => { setShowProfile(!showProfile); setShowNotifications(false); setShowActivity(false); }}
            style={{ 
              width: '32px', 
              height: '32px', 
              borderRadius: '50%', 
              backgroundColor: showProfile ? 'var(--primary-color)' : 'var(--sidebar-active)', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}>
            <User size={18} color={showProfile ? '#fff' : 'currentColor'} />
          </div>
          {showProfile && (
            <div className="card" style={{ position: 'absolute', top: '40px', right: 0, width: '150px', zIndex: 1000, padding: '5px 0' }}>
              <div className="nav-link" style={{ padding: '8px 15px', cursor: 'pointer' }}>Profile Settings</div>
              <div className="nav-link" style={{ padding: '8px 15px', cursor: 'pointer', color: 'var(--danger-color)' }}>Logout</div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
