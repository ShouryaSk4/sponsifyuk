import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const Register = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        setLoading(true);

        try {
            const res = await axios.post(`${API_URL}/users/register`, {
                username: email.split('@')[0], // Generate a fallback username
                email,
                password
            });

            if (res.data.success) {
                // Route to login page on success
                navigate('/login');
            } else {
                setError(res.data.error || 'Registration failed');
            }
        } catch (err) {
            console.error("Registration Error:", err);
            setError(err.response?.data?.error || 'An error occurred during registration');
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div className="page-banner-area bg-f0f4fc">
                <div className="container">
                    <div className="page-banner-content">
                        <h1>Register</h1>
                        <ul>
                            <li><Link to="/">Home</Link></li>
                            <li>Register</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div className="register-area ptb-50">
                <div className="container">
                    <div className="register">
                        <h3>Register</h3>
                        {error && <div className="alert alert-danger">{error}</div>}
                        <form onSubmit={handleRegister}>
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
                            <div className="form-group">
                                <input 
                                    type="password" 
                                    className="form-control" 
                                    placeholder="Confirm Password*" 
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                />
                            </div>
                            <button type="submit" className="default-btn btn" disabled={loading}>
                                {loading ? 'Registering...' : 'Register'}
                            </button>
                            <p className="pt-50">Already registered? <Link to="/login">Login</Link></p>
                        </form>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Register;
