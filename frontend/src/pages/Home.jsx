import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import JobCard from '../components/JobCard';
import Autocomplete from '../components/Autocomplete';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const Home = () => {
    const [categories, setCategories] = useState([]);
    const [featuredJobs, setFeaturedJobs] = useState([]);
    const [stats, setStats] = useState({ total_jobs: 0, total_companies: 0, total_domains: 0, total_members: 0 });
    const [searchTitle, setSearchTitle] = useState('');
    const [searchLocation, setSearchLocation] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        // Fetch Top Categories
        axios.get(`${API_URL}/categories/top`)
            .then(res => {
                if (res.data.success) {
                    setCategories(res.data.categories || []);
                }
            })
            .catch(err => console.error("Error fetching categories:", err));

        // Fetch Featured Jobs
        axios.get(`${API_URL}/jobs/featured?limit=6`)
            .then(res => {
                if (res.data.success) {
                    setFeaturedJobs(res.data.jobs || []);
                }
            })
            .catch(err => console.error("Error fetching jobs:", err));

        // Fetch Stats
        axios.get(`${API_URL}/stats`)
            .then(res => {
                if (res.data.success) {
                    setStats(res.data.stats || {});
                }
            })
            .catch(err => console.error("Error fetching stats:", err));
    }, []);

    const handleSearch = (e) => {
        e.preventDefault();
        const params = new URLSearchParams();
        if (searchTitle) params.append('q', searchTitle);
        if (searchLocation) params.append('location', searchLocation);
        navigate(`/job-listing?${params.toString()}`);
    };

    return (
        <>
            <div className="banner-area style2">
                <div className="container-fluid">
                    <div className="row align-items-center">
                        <div className="col-lg-6">
                            <div className="banner-content style2">
                                <div className="banner-title">
                                    <h1>We'll Help You To Find Your Desire Job</h1>
                                </div>
                                <div className="serech-over">
                                    <span>Search Over 70,000 Jobs Today!</span>
                                </div>
                                <div className="banner-search-form style-2">
                                    <form onSubmit={handleSearch}>
                                        <div className="row g-0 align-items-center">
                                            <div className="col-lg-4 col-sm-6">
                                                <Autocomplete 
                                                    value={searchTitle}
                                                    onChange={setSearchTitle}
                                                    placeholder="Job Title"
                                                    iconClass="fa-solid fa-briefcase"
                                                    type="title"
                                                />
                                            </div>
                                            <div className="col-lg-4 col-sm-6">
                                                <Autocomplete 
                                                    value={searchLocation}
                                                    onChange={setSearchLocation}
                                                    placeholder="Location"
                                                    iconClass="fa-solid fa-location-dot"
                                                    type="location"
                                                />
                                            </div>
                                            <div className="col-lg-4 col-sm-12">
                                                <div className="search-btn">
                                                    <button type="submit" className="default-btn btn">
                                                        <i className="fa-solid fa-magnifying-glass"></i> Search Jobs
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-6">
                            <div className="banner-image-content-style2">
                                <img src="/assets/images/banner-img-4.png" alt="Banner" />
                                <div className="assisted-candidate">
                                    <div className="icon">
                                        <img src="/assets/images/icon-1.png" alt="Icon" />
                                    </div>
                                    <h3>50K+</h3>
                                    <span>Assisted Candidate</span>
                                </div>
                                <div className="creative-agency">
                                    <div className="icon">
                                        <i className="fa-solid fa-suitcase"></i>
                                    </div>
                                    <h3>Creative Agency</h3>
                                    <span>Upload Your CV</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="categories-area pb-70">
                <div className="container">
                    <div className="title">
                        <div className="row align-items-center">
                            <div className="col-lg-8 col-md-9">
                                <div className="section-title style2">
                                    <h2>Most Demanded Jobs Categories</h2>
                                </div>
                            </div>
                            <div className="col-lg-4 col-md-3">
                                <div className="browse-btn">
                                    <Link to="/job-listing" className="default-btn btn">View All Categories</Link>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="row">
                        {categories.map((cat, index) => (
                            <div className="col-lg-3 col-sm-6" key={index}>
                                <div className="single-categories-box">
                                    <div className="icon">
                                        <i className={`fa-solid ${cat.icon || 'fa-briefcase'}`}></i>
                                    </div>
                                    <h3>{cat.name || 'Other'}</h3>
                                    <span>({cat.count} Open Positions)</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="featured-job-area ptb-100 bg-f0f5f7">
                <div className="container">
                    <div className="title">
                        <div className="row align-items-center">
                            <div className="col-lg-8 col-md-9">
                                <div className="section-title style2">
                                    <h2>Featured Jobs</h2>
                                    <p>Here are some of the latest jobs that have been added.</p>
                                </div>
                            </div>
                            <div className="col-lg-4 col-md-3">
                                <div className="browse-btn">
                                    <Link to="/job-listing" className="default-btn btn">Browse All Jobs</Link>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="row">
                         {featuredJobs.map(job => (
                             <JobCard key={job.id} job={job} isFeatured={true} />
                         ))}
                    </div>
                </div>
            </div>

            {/* Start Counter Area */}
            <div className="counters-area bg-f0f5f7 pt-100 pb-70">
                <div className="container">
                    <div className="section-title">
                        <h2>SponsifyUK Numbers</h2>
                    </div>
                    <div className="row">
                        <div className="col-lg-3 col-md-3 col-6">
                            <div className="single-counter-item style-2">
                                <div className="icon">
                                    <i className="fa-solid fa-calendar-plus"></i>
                                </div>
                                <h1>
                                    <span className="odometer odometer-auto-theme">{(stats.total_jobs || 0).toLocaleString()}</span>
                                </h1>
                                <p>Total Jobs Added</p>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-3 col-6">
                            <div className="single-counter-item style-2">
                                <div className="icon">
                                    <i className="fa-solid fa-building"></i>
                                </div>
                                <h1>
                                    <span className="odometer odometer-auto-theme">{(stats.total_companies || 0).toLocaleString()}</span>
                                </h1>
                                <p>Total Sponsored Companies</p>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-3 col-6">
                            <div className="single-counter-item style-2">
                                <div className="icon">
                                    <i className="fa-solid fa-hospital-user"></i>
                                </div>
                                <h1>
                                    <span className="odometer odometer-auto-theme">{(stats.total_domains || 0).toLocaleString()}</span>
                                </h1>
                                <p>Total Live Domains</p>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-3 col-6">
                            <div className="single-counter-item style-2">
                                <div className="icon">
                                    <i className="fa-solid fa-person-burst"></i>
                                </div>
                                <h1>
                                    <span className="odometer odometer-auto-theme">{(stats.total_members || 0).toLocaleString()}</span>
                                </h1>
                                <p>Total Members</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {/* End Counter Area */}

            {/* Start Subscribe Area */}
            <div className="subscribe-area bg-f0f5f7">
                <div className="container">
                    <div className="row align-items-center">
                        <div className="col-lg-5">
                            <div className="subsceibe-left-content">
                                <h2>Subscribe Our Newsletter</h2>
                            </div>
                        </div>
                        <div className="col-lg-7">
                            <div className="subscribe-form">
                                <form className="newsletter-form" onSubmit={(e) => e.preventDefault()}>
                                    <input type="email" className="form-control" placeholder="Your Email" name="EMAIL" required autoComplete="off" />
                                    <button className="default-btn" type="submit">Subscribe Now </button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {/* End Subscribe Area */}
        </>
    );
};

export default Home;
