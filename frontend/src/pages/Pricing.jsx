import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const Pricing = () => {
    const navigate = useNavigate();
    const [loadingTier, setLoadingTier] = useState(null);

    const handleCheckout = async (e, tier) => {
        e.preventDefault();
        
        const stored = localStorage.getItem('sponsify_user');
        if (!stored) {
            alert("Please login first to subscribe to a plan.");
            navigate('/login');
            return;
        }

        let user;
        try {
            user = JSON.parse(stored);
        } catch (err) {
            navigate('/login');
            return;
        }

        if (!user || !user.user_id) {
            navigate('/login');
            return;
        }

        setLoadingTier(tier);

        try {
            const res = await axios.post(`${API_URL}/create-checkout-session`, {
                user_id: user.user_id,
                tier: tier
            });

            if (res.data.success && res.data.checkout_url) {
                window.location.href = res.data.checkout_url;
            } else if (res.data.already_premium) {
                alert(res.data.message);
                navigate('/job-listing');
            } else {
                alert(res.data.error || "Failed to initiate checkout");
            }
        } catch (err) {
            console.error("Checkout Error:", err);
            alert(err.response?.data?.error || "An error occurred during checkout setup.");
        } finally {
            setLoadingTier(null);
        }
    };

    return (
        <>
            <div className="page-banner-area bg-f0f4fc">
                <div className="container">
                    <div className="page-banner-content">
                        <h1>Pricing Plan</h1>
                        <ul>
                            <li><Link to="/">Home</Link></li>
                            <li>Pricing Plan</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div className="pricing-area pt-100 pb-70">
                <div className="container">
                    <div className="section-title">
                        <h2>Choose the plan that fits your needs</h2>
                        <p>Unlock access to the best jobs in the UK. Upgrade today to remove limits and view premium listings instantly.</p>
                    </div>
                    <div className="row justify-content-center">
                        {/* Plan 1 */}
                        <div className="col-lg-4 col-sm-6">
                            <div className="single-pricing-card">
                                <div className="pricing-top-content">
                                    <h3>Basic Plan</h3>
                                    <h1>£10<span>/Month</span></h1>
                                </div>
                                <div className="features-list">
                                    <ul>
                                        <li><i className="fa-solid fa-check text-success"></i> Access to Top 1000 Jobs</li>
                                        <li><i className="fa-solid fa-check text-success"></i> Sort by Recently Added</li>
                                        <li><i className="fa-solid fa-xmark text-danger"></i> Highlighted Posts</li>
                                        <li><i className="fa-solid fa-xmark text-danger"></i> Unlimited Access</li>
                                    </ul>
                                </div>
                                <button 
                                    onClick={(e) => handleCheckout(e, 1)} 
                                    className="default-btn btn w-100"
                                    disabled={loadingTier !== null}
                                >
                                    {loadingTier === 1 ? 'Processing...' : 'Get Started Now'}
                                </button>
                            </div>
                        </div>

                        {/* Plan 2 */}
                        <div className="col-lg-4 col-sm-6">
                            <div className="single-pricing-card">
                                <div className="pricing-top-content">
                                    <h3>Extended Plan</h3>
                                    <h1>£20<span>/Month</span></h1>
                                </div>
                                <div className="features-list">
                                    <ul>
                                        <li><i className="fa-solid fa-check text-success"></i> Access to Top 3000 Jobs</li>
                                        <li><i className="fa-solid fa-check text-success"></i> Sort by Recently Added</li>
                                        <li><i className="fa-solid fa-check text-success"></i> Highlighted Posts</li>
                                        <li><i className="fa-solid fa-xmark text-danger"></i> Unlimited Access</li>
                                    </ul>
                                </div>
                                <button 
                                    onClick={(e) => handleCheckout(e, 2)} 
                                    className="default-btn btn w-100"
                                    disabled={loadingTier !== null}
                                >
                                    {loadingTier === 2 ? 'Processing...' : 'Get Started Now'}
                                </button>
                            </div>
                        </div>

                        {/* Plan 3 */}
                        <div className="col-lg-4 col-sm-6">
                            <div className="single-pricing-card">
                                <div className="pricing-top-content">
                                    <h3>Premium Plan</h3>
                                    <h1>£30<span>/Month</span></h1>
                                </div>
                                <div className="features-list">
                                    <ul>
                                        <li><i className="fa-solid fa-check text-success"></i> Unlimited Job Access</li>
                                        <li><i className="fa-solid fa-check text-success"></i> Sort by Recently Added</li>
                                        <li><i className="fa-solid fa-check text-success"></i> Highlighted Posts</li>
                                        <li><i className="fa-solid fa-check text-success"></i> Family / Multi-user</li>
                                        <li><i className="fa-solid fa-star text-warning"></i> AI Resume Generation (UK Format) <span className="badge bg-info ms-1" style={{ fontSize: '10px' }}>Coming Soon</span></li>
                                    </ul>
                                </div>
                                <button 
                                    onClick={(e) => handleCheckout(e, 3)} 
                                    className="default-btn btn w-100"
                                    disabled={loadingTier !== null}
                                >
                                    {loadingTier === 3 ? 'Processing...' : 'Get Started Now'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Pricing;
