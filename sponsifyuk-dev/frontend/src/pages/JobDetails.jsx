import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';
import JobCard from '../components/JobCard';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const JobDetails = () => {
    const [searchParams] = useSearchParams();
    const jobId = searchParams.get('job_id');
    
    const [job, setJob] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [relatedJobs, setRelatedJobs] = useState([]);

    useEffect(() => {
        if (!jobId) {
            setError('No Job ID provided.');
            setLoading(false);
            return;
        }

        setLoading(true);
        // Fetch Job Details
        axios.get(`${API_URL}/jobs/${jobId}`)
            .then(res => {
                if (res.data.success && res.data.job) {
                    setJob(res.data.job);
                    // Optionally fetch related jobs by category or just featured ones
                    fetchRelatedJobs(res.data.job.job_category_id);
                } else {
                    setError('Job not found.');
                }
            })
            .catch(err => {
                console.error("Error fetching job:", err);
                setError('Failed to load job details.');
            })
            .finally(() => setLoading(false));
    }, [jobId]);

    const fetchRelatedJobs = (categoryId) => {
        const payload = { limit: 3, page: 1 };
        if (categoryId) payload.category = categoryId;
        
        axios.post(`${API_URL}/jobs/search`, payload)
            .then(res => {
                if (res.data.success && res.data.jobs) {
                    // Filter out the current job
                    setRelatedJobs(res.data.jobs.filter(j => j.id.toString() !== jobId).slice(0, 3));
                }
            })
            .catch(err => console.error(err));
    };

    const handleApply = (e) => {
        e.preventDefault();
        // The original logic would trigger an application tracking API call if logged in,
        // and then redirect to the job's external link. 
        // For now, let's just redirect to the job link.
        if (job && job.job_link) {
            window.open(job.job_link, '_blank');
        } else {
            alert("No application link available.");
        }
    };

    if (loading) {
        return (
            <div className="container ptb-100 text-center">
                <i className="fa-solid fa-spinner fa-spin fa-3x" style={{color: '#1d90c9'}}></i>
                <h3 className="mt-3">Loading Job Details...</h3>
            </div>
        );
    }

    if (error || !job) {
        return (
            <div className="container ptb-100 text-center">
                <h3>{error || 'Job not found'}</h3>
                <Link to="/job-listing" className="default-btn btn mt-3">Back to Jobs</Link>
            </div>
        );
    }

    const postedDate = job.dateposted ? new Date(job.dateposted).toLocaleDateString() : 'N/A';
    const salary = job.salary && job.salary !== 'Not Specified' ? job.salary : 'Not Specified';
    
    return (
        <>
            <div className="job-details-banner-area bg-f0f4fc">
                <div className="container">
                    <div className="job-details-banner-content">
                        <div className="row align-items-center">
                            <div className="col-lg-7 col-md-8">
                                <div className="job-details-banner-left-content" id="job-banner-content" style={{ minHeight: '120px' }}>
                                    <div className="img">
                                        <i className="fa-solid fa-building" style={{ fontSize: '36px', color: '#6c63ff' }}></i>
                                    </div>
                                    <span>{job.organisation_name || 'Company Name'}</span>
                                    <h2>{job.job_title}</h2>
                                    <div className="info">
                                        <ul>
                                            <li><i className="flaticon-location"></i><span>{job.location || job.org_location || 'UK'}</span></li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                            <div className="col-lg-5 col-md-4">
                                <div className="job-details-banner-right-content">
                                    <a href="#" onClick={handleApply} className="default-btn btn">Apply Now</a>
                                    <div className="share-content">
                                        <ul>
                                            <li><span><i className="fa-solid fa-share-nodes"></i>Share</span></li>
                                            <li><a href="https://www.facebook.com/" target="_blank" rel="noreferrer"><i className="fa-brands fa-facebook-f"></i></a></li>
                                            <li><a href="https://www.twitter.com/" target="_blank" rel="noreferrer"><i class="fa-brands fa-twitter"></i></a></li>
                                            <li><a href="https://instagram.com/" target="_blank" rel="noreferrer"><i className="fa-brands fa-instagram"></i></a></li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="job-details-area pt-100 pb-70">
                <div className="container">
                    <div className="row">
                        <div className="col-lg-8">
                            <div className="job-details-content">
                                <div className="job-description">
                                    <h3>Job Description</h3>
                                    <div 
                                        style={{ lineHeight: '1.8' }}
                                        dangerouslySetInnerHTML={{ 
                                            __html: (job.job_description || 'No description provided.')
                                                        .replace(/\uFFFD/g, '•')
                                                        .replace(/\n/g, '<br />') 
                                        }} 
                                    />
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-4">
                            <div className="sidebar">
                                <div className="single-sidebar-widget job-alert style2">
                                    <h3>Find A Job</h3>
                                    <p>Create a job alert now and never miss any job update.</p>
                                    <form onSubmit={(e) => e.preventDefault()}>
                                        <div className="form-group">
                                            <input className="form-control" type="email" placeholder="Email Address" />
                                        </div>
                                        <button type="submit" className="default-btn btn">Create Job Alert</button>
                                    </form>
                                </div>
                                <div className="single-sidebar-widget job-overview">
                                    <h3>Job Overview</h3>
                                    <ul>
                                        <li><span>Published On:</span> {postedDate}</li>
                                        <li><span>Job Type:</span> {job.remote_type || 'Full Time'}</li>
                                        <li><span>Experience:</span> {job.experience_level || 'Entry Level'}</li>
                                        <li><span>Job Location:</span> {job.location || job.org_location || 'UK'}</li>
                                        <li><span>Salary:</span> {salary}</li>
                                        <li><span>Source:</span> {job.job_source || 'SponsifyUK'}</li>
                                    </ul>
                                </div>
                                <div className="single-sidebar-widget location style2">
                                    <h3>Company Overview</h3>
                                    <ul>
                                        <li><span>Company Name:</span> {job.organisation_name}</li>
                                        {job.company_url && (
                                            <li><span>Website:</span> <a href={job.company_url.startsWith('http') ? job.company_url : `https://${job.company_url}`} target="_blank" rel="noreferrer">Visit Site</a></li>
                                        )}
                                        <li><span>Location:</span> {job.org_location || job.location || 'UK'}</li>
                                        <li><span>Email:</span> <a href="mailto:support@sponsifyuk.com">support@sponsifyuk.com</a></li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {relatedJobs.length > 0 && (
                <div className="related-job-area bg-f0f5f7 pt-100 pb-70">
                    <div className="container">
                        <h3>Related Jobs</h3>
                        <div className="row justify-content-center">
                            {relatedJobs.map(related => (
                                <JobCard key={related.id} job={related} />
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default JobDetails;
