import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const Navbar = () => {
    const [user, setUser] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        const checkUser = () => {
            const stored = localStorage.getItem('sponsify_user');
            if (stored) {
                try {
                    setUser(JSON.parse(stored));
                } catch (e) {
                    console.error("Error parsing user from local storage", e);
                }
            } else {
                setUser(null);
            }
        };

        checkUser();
        window.addEventListener('auth-change', checkUser);
        return () => window.removeEventListener('auth-change', checkUser);
    }, []);

    const handleLogout = (e) => {
        e.preventDefault();
        localStorage.removeItem('sponsify_user');
        setUser(null);
        window.dispatchEvent(new Event('auth-change'));
        navigate('/login');
    };

    return (
        <div className="navbar-area is-sticky">
            <div className="mobile-responsive-nav">
                <div className="container">
                    <div className="mobile-responsive-menu">
                        <div className="logo">
                            <Link to="/">
                                <img src="/assets/images/logo.jpg" className="main-logo" alt="logo" width="200" />
                                <img src="/assets/images/logo.jpg" className="white-logo" alt="logo" width="200" />
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
            <div className="desktop-nav">
                <div className="container-fluid">
                    <nav className="navbar navbar-expand-md navbar-light">
                        <Link className="navbar-brand" to="/">
                            <img src="/assets/images/logo.jpg" className="main-logo" alt="logo" width="200" />
                            <img src="/assets/images/logo.jpg" className="white-logo" alt="logo" width="200" />
                        </Link>
                        <div className="collapse navbar-collapse mean-menu" id="navbarSupportedContent" style={{ display: "block" }}>
                            <ul className="navbar-nav me-auto">
                                <li className="nav-item">
                                    <Link to="/" className="nav-link">Home</Link>
                                </li>
                                <li className="nav-item">
                                    <Link to="/pricing" className="nav-link">Pricing</Link>
                                </li>
                                <li className="nav-item">
                                    <a href="#" className="nav-link dropdown-toggle">Jobs</a>
                                    <ul className="dropdown-menu">
                                        <li className="nav-item">
                                            <Link to="/job-listing" className="nav-link">Job Listing</Link>
                                        </li>
                                    </ul>
                                </li>
                                <li className="nav-item">
                                    <a href="#" className="nav-link dropdown-toggle">Categories</a>
                                    <ul className="dropdown-menu">
                                        <li className="nav-item"><Link to="/job-listing?category=1" className="nav-link">🖥️ Technology &amp; Engineering</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=2" className="nav-link">💼 Business &amp; Management</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=4" className="nav-link">📊 Finance &amp; Accounting</Link></li>
                                        <li className="nav-item"><Link to="/job-listing" className="nav-link">📢 Marketing, Sales &amp; Communication</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=6" className="nav-link">🎨 Design &amp; Creative</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=7" className="nav-link">🧑‍⚕️ Healthcare &amp; Life Sciences</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=8" className="nav-link">🏗️ Construction, Manufacturing &amp; Trades</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=9" className="nav-link">🧪 Science &amp; Research</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=10" className="nav-link">🎓 Education &amp; Training</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=11" className="nav-link">⚖️ Legal &amp; Public Policy</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=12" className="nav-link">🚚 Logistics, Supply Chain &amp; Transportation</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=13" className="nav-link">🛍️ Retail, Hospitality &amp; Tourism</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=14" className="nav-link">🧑‍🤝‍🧑 Human Resources &amp; Administration</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=15" className="nav-link">🔐 Security &amp; Protective Services</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=16" className="nav-link">🌱 Agriculture, Energy &amp; Sustainability</Link></li>
                                        <li className="nav-item"><Link to="/job-listing?category=17" className="nav-link">🎮 Media, Entertainment &amp; Gaming</Link></li>
                                    </ul>
                                </li>
                            </ul>
                            <div className="others-options">
                                {user ? (
                                    <div className="option-item d-flex align-items-center" style={{ gap: '15px' }}>
                                        <span className="fw-bold">Hi, {user.username || user.email?.split('@')[0]}</span>
                                        <button onClick={handleLogout} className="default-btn btn style-2 border-0">Logout</button>
                                    </div>
                                ) : (
                                    <div className="option-item">
                                        <Link to="/login" className="default-btn btn style-2"><i className="fa-regular fa-user"></i> Login / Register</Link>
                                    </div>
                                )}
                            </div>
                        </div>
                    </nav>
                </div>
            </div>
            <div className="others-option-for-responsive">
                <div className="container">
                    <div className="dot-menu">
                        <div className="inner">
                            <div className="circle circle-one"></div>
                            <div className="circle circle-two"></div>
                            <div className="circle circle-three"></div>
                        </div>
                    </div>
                    <div className="container">
                        <div className="option-inner">
                            <div className="others-options justify-content-center d-flex align-items-center">
                                <div className="others-options">
                                    {user ? (
                                        <div className="option-item">
                                            <button onClick={handleLogout} className="default-btn btn style-2 border-0 w-100 mb-2">Logout</button>
                                        </div>
                                    ) : (
                                        <div className="option-item">
                                            <Link to="/login" className="default-btn btn style-2"><i className="fa-regular fa-user"></i> Login / Register</Link>
                                        </div>
                                    )}
                                    <div className="option-item">
                                        <Link to="/post-job" className="default-btn btn">Post New Job</Link>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Navbar;
