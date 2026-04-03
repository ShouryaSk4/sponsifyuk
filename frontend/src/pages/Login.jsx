import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const res = await axios.post(`${API_URL}/users/login`, {
                email,
                password
            });

            if (res.data.success && res.data.user) {
                // Store user data in localStorage
                localStorage.setItem('sponsify_user', JSON.stringify(res.data.user));
                
                // Route to previous page or Job Listing
                navigate('/job-listing');
                
                // Optionally dispatch an event to update Navbar state
                window.dispatchEvent(new Event('auth-change'));
            } else {
                setError(res.data.error || 'Invalid credentials');
            }
        } catch (err) {
            console.error("Login Error:", err);
            setError(err.response?.data?.error || 'An error occurred during login');
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div className="page-banner-area bg-f0f4fc">
                <div className="container">
                    <div className="page-banner-content">
                        <h1>Login</h1>
                        <ul>
                            <li><Link to="/">Home</Link></li>
                            <li>Login</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div className="login-area ptb-50">
                <div className="container">
                    <div className="login">
                        <h3>Log In</h3>
                        {error && <div className="alert alert-danger">{error}</div>}
                        <form onSubmit={handleLogin}>
                            <div className="form-group">
                                <input 
                                    type="email" 
                                    className="form-control" 
                                    placeholder="Username Or Email Address*" 
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <input 
                                    type="password" 
                                    className="form-control" 
                                    placeholder="Password*" 
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="form-check">
                                <input className="form-check-input" type="checkbox" id="flexCheckDefault" />
                                <label className="form-check-label" htmlFor="flexCheckDefault">
                                    Remember Me
                                </label>
                            </div>
                            <button type="submit" className="default-btn btn" disabled={loading}>
                                {loading ? 'Logging in...' : 'Login'}
                            </button>
                            <a href="#">Lost your password?</a>
                            <Link to="/register">Create an account</Link>
                        </form>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Login;
