import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import JobCard from '../components/JobCard';
import Autocomplete from '../components/Autocomplete';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const JobListing = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const [jobs, setJobs] = useState([]);
    const [totalJobs, setTotalJobs] = useState(0);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    // Filter states
    const [query, setQuery] = useState(searchParams.get('q') || '');
    const [location, setLocation] = useState(searchParams.get('location') || '');
    const [category, setCategory] = useState(searchParams.get('category') || '');
    const [remoteType, setRemoteType] = useState('');
    const [experienceLevel, setExperienceLevel] = useState('');
    const [locationFilter, setLocationFilter] = useState('');

    useEffect(() => {
        fetchJobs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [page, category, remoteType, experienceLevel, locationFilter]); // Fetch when these change

    const fetchJobs = () => {
        setLoading(true);
        const stored = localStorage.getItem('sponsify_user');
        let userId = null;
        if (stored) {
            try { userId = JSON.parse(stored).user_id; } catch(e){}
        }

        const payload = {
            query: query,
            location: location,
            category: category,
            remote_type: remoteType,
            experience_level: experienceLevel,
            page: page,
            limit: 10,
            user_id: userId,
            location_filter: locationFilter
        };

        axios.post(`${API_URL}/jobs/search`, payload)
            .then(res => {
                if (res.data.success) {
                    setJobs(res.data.jobs || []);
                    setTotalJobs(res.data.total || 0);
                    setTotalPages(res.data.total_pages || 1);
                }
            })
            .catch(err => console.error("Error searching jobs", err))
            .finally(() => setLoading(false));
    };

    const handleSearchSubmit = (e) => {
        e.preventDefault();
        setPage(1);
        setSearchParams({ q: query, location, category });
        fetchJobs();
    };

    const handleFilterClick = (e, setter, value) => {
        e.preventDefault();
        setter(value);
        setPage(1);
    };

    return (
        <>
            <div className="page-banner-area bg-f0f4fc">
                <div className="container">
                    <div className="page-banner-content">
                        <h1>Job Listing</h1>
                        <ul>
                            <li><a href="/">Home</a></li>
                            <li>Job Listing</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div className="job-listing-area pt-50 pb-70">
                <div className="container">
                    <div className="job-listing-search-form">
                        <form onSubmit={handleSearchSubmit}>
                            <div className="row g-0">
                                <div className="col-lg-3 col-sm-6">
                                    <Autocomplete 
                                        value={query}
                                        onChange={setQuery}
                                        placeholder="Keywords / Job Title"
                                        iconClass="fa-solid fa-address-book"
                                        type="title"
                                    />
                                </div>
                                <div className="col-lg-3 col-sm-6">
                                    <Autocomplete 
                                        value={location}
                                        onChange={setLocation}
                                        placeholder="City Or Postcode"
                                        iconClass="fa-solid fa-magnifying-glass-location"
                                        type="location"
                                    />
                                </div>
                                <div className="col-lg-4 col-sm-6">
                                    <div className="form-group style">
                                        <select 
                                            className="form-select form-control" 
                                            value={category} 
                                            onChange={(e) => { setCategory(e.target.value); setPage(1); }}
                                        >
                                            <option value="">All Categories</option>
                                            <option value="1">Technology &amp; Engineering</option>
                                            <option value="2">Business &amp; Management</option>
                                            <option value="4">Finance &amp; Accounting</option>
                                            <option value="5">Marketing, Sales &amp; Communication</option>
                                            <option value="6">Design &amp; Creative</option>
                                            <option value="7">Healthcare &amp; Life Sciences</option>
                                            <option value="8">Construction, Manufacturing &amp; Trades</option>
                                            <option value="9">Science &amp; Research</option>
                                            <option value="10">Education &amp; Training</option>
                                            <option value="11">Legal &amp; Public Policy</option>
                                            <option value="12">Logistics, Supply Chain &amp; Transportation</option>
                                            <option value="13">Retail, Hospitality &amp; Tourism</option>
                                            <option value="14">Human Resources &amp; Administration</option>
                                            <option value="15">Security &amp; Protective Services</option>
                                            <option value="16">Agriculture, Energy &amp; Sustainability</option>
                                            <option value="17">Media, Entertainment &amp; Gaming</option>
                                        </select>
                                        <i className="fa-solid fa-clipboard-list"></i>
                                    </div>
                                </div>
                                <div className="col-lg-2 col-sm-6">
                                    <div className="search-btn">
                                        <button type="submit" className="default-btn btn">Find Jobs</button>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>

                    <div className="row">
                        <div className="col-lg-8">
                            <div className="job-listing-content">
                                <div className="search-job-top-content">
                                    <div className="row align-items-center">
                                        <div className="col-lg-6 col-md-4">
                                            <div className="shoing-content">
                                                <span>Showing {(page - 1) * 10 + 1} – {Math.min(page * 10, totalJobs)} of {totalJobs} results</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="row justify-content-center">
                                    {loading ? (
                                        <div className="col-12 text-center py-5">
                                            <i className="fa-solid fa-spinner fa-spin fa-2x" style={{ color: '#1d90c9' }}></i>
                                            <p className="mt-3">Searching jobs...</p>
                                        </div>
                                    ) : jobs.length > 0 ? (
                                        jobs.map(job => <JobCard key={job.id} job={job} />)
                                    ) : (
                                        <div className="col-12 text-center py-5">
                                            <h4>No jobs found matching your search.</h4>
                                            <p>Try different keywords or broaden your filters.</p>
                                        </div>
                                    )}
                                </div>

                                {(() => {
                                    if (totalPages <= 1) return null;
                                    let startPage = Math.max(1, page - 4);
                                    let endPage = Math.min(totalPages, startPage + 9);
                                    if (endPage - startPage < 9) {
                                        startPage = Math.max(1, endPage - 9);
                                    }
                                    const pages = [];
                                    for (let i = startPage; i <= endPage; i++) {
                                        pages.push(i);
                                    }
                                    return (
                                        <div className="paginations mb-30">
                                            <ul>
                                                <li>
                                                    <a href="#" onClick={(e) => { e.preventDefault(); setPage(prev => Math.max(1, prev - 1)); }} className={page === 1 ? 'disabled' : ''}>
                                                        <i className="fa-solid fa-angle-left"></i>
                                                    </a>
                                                </li>
                                                {pages.map(p => (
                                                    <li key={p}>
                                                        <a href="#" onClick={(e) => { e.preventDefault(); setPage(p); }} className={page === p ? 'active' : ''}>
                                                            {p}
                                                        </a>
                                                    </li>
                                                ))}
                                                <li>
                                                    <a href="#" onClick={(e) => { e.preventDefault(); setPage(prev => Math.min(totalPages, prev + 1)); }} className={page === totalPages ? 'disabled' : ''}>
                                                        <i className="fa-solid fa-angle-right"></i>
                                                    </a>
                                                </li>
                                            </ul>
                                        </div>
                                    );
                                })()}
                            </div>
                        </div>

                        <div className="col-lg-4">
                            <div className="sidebar">
                                <div className="single-sidebar-widget job-alert">
                                    <h3>Create Job Alert</h3>
                                    <p>Create a job alert now and never miss any job update.</p>
                                    <form onSubmit={(e) => e.preventDefault()}>
                                        <div className="form-group">
                                            <input className="form-control" type="text" placeholder="Keywords / Job Title" />
                                        </div>
                                        <button type="submit" className="default-btn btn">Create Job Alert</button>
                                    </form>
                                </div>
                                <div className="single-sidebar-widget range">
                                    <h3>Location Filter</h3>
                                    <ul>
                                        <li>
                                            <a href="#" onClick={(e) => { e.preventDefault(); setLocationFilter(locationFilter === 'uk' ? '' : 'uk'); setPage(1); }} className={locationFilter === 'uk' ? 'text-primary fw-bold' : ''}>
                                                🇬🇧 UK Jobs Only
                                            </a>
                                        </li>
                                        <li>
                                            <a href="#" onClick={(e) => { e.preventDefault(); setLocationFilter(locationFilter === 'london' ? '' : 'london'); setPage(1); }} className={locationFilter === 'london' ? 'text-primary fw-bold' : ''}>
                                                🏙️ London Jobs
                                            </a>
                                        </li>
                                        <li>
                                            <a href="#" onClick={(e) => { e.preventDefault(); setLocationFilter(''); setPage(1); }} className={locationFilter === '' ? 'text-primary fw-bold' : ''}>
                                                🌍 All Locations
                                            </a>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default JobListing;
