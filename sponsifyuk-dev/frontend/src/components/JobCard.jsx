import React from 'react';
import { Link } from 'react-router-dom';

const JobCard = ({ job, isFeatured = false }) => {
    let daysAgo = '';
    if (job.dateposted) {
        const posted = new Date(job.dateposted);
        if (!isNaN(posted.getTime())) {
            const d = Math.floor((Date.now() - posted) / 86400000);
            daysAgo = d === 0 ? 'Today' : `${d} Day${d === 1 ? '' : 's'} Ago`;
        }
    }

    const salary = job.salary && job.salary !== 'Not Specified' ? job.salary : '';
    let location = job.location || job.org_location || 'UK';
    // Clean up strings like "locations\nLondon", "Locations: London", or "[Location]"
    location = location.replace(/^(?:locations?[\s:\n-]+|\[location\]\s*)/i, '').trim() || 'Location Not Specified';
    
    const jobType = job.remote_type || 'Fulltime';

    const cardClasses = `single-job-card ${isFeatured ? 'style-2' : ''}`;

    if (job.is_blurred) {
        return (
            <div className="col-lg-6 col-md-6 mb-4">
                <div className={`single-job-card ${isFeatured ? 'style-2' : ''} position-relative`} style={{ overflow: 'hidden' }}>
                    <div className="job-content" style={{ filter: 'blur(5px)', pointerEvents: 'none', userSelect: 'none' }}>
                        <div className="d-flex justify-content-between align-items-center mb-2">
                            <span className="time">Fulltime</span>
                        </div>
                        <h2><a href="#">Premium Job Listing</a></h2>
                        <div className="info"><ul><li><i className="flaticon-location"></i>Hidden</li></ul></div>
                        <div className="bottom-content">
                            <ul className="d-flex">
                                <li><div className="left-content"><div className="icon"><i className="fa-solid fa-building" style={{ color: '#6c63ff' }}></i></div><span>Unlock to View</span></div></li>
                            </ul>
                        </div>
                    </div>
                    <div className="position-absolute w-100 h-100 top-0 start-0 d-flex flex-column justify-content-center align-items-center" style={{ backgroundColor: 'rgba(255,255,255,0.7)', zIndex: 10 }}>
                        <i className="fa-solid fa-lock mb-2" style={{ fontSize: '30px', color: '#1d90c9' }}></i>
                        <h4 className="fw-bold mb-1">Premium Result</h4>
                        <Link to="/pricing" className="btn default-btn btn-sm mt-3">Upgrade to View</Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="col-lg-6 col-md-6 mb-4">
            <div className={cardClasses}>
                <div className="job-content" style={!isFeatured ? { paddingTop: '25px' } : undefined}>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <span className="time">{jobType}</span>
                            {job.exists_in_uk === 0 && (
                                <span className="time" style={{ backgroundColor: '#f7c500', color: '#000', marginLeft: '8px' }}>
                                    Remote / Global Job
                                </span>
                            )}
                        </div>
                        {/* We will handle bookmarks via separate state/click handler later if needed */}
                        <a href="#" className="spk-bookmark" onClick={(e) => e.preventDefault()}>
                            <i className="fa-regular fa-bookmark" style={{ color: '#bbb', fontSize: '16px' }}></i>
                        </a>
                    </div>
                    <h2>
                        <Link to={`/job-details?job_id=${job.id}`}>{job.job_title}</Link>
                    </h2>
                    <div className="info">
                        <ul>
                            {daysAgo && <li><i className="flaticon-time"></i>{daysAgo}</li>}
                            <li><i className="flaticon-location"></i>{location}</li>
                        </ul>
                    </div>
                    <div className="bottom-content">
                        <ul className="d-flex">
                            <li>
                                <div className="left-content">
                                    <div className="icon">
                                        <i className="fa-solid fa-building" style={!isFeatured ? { fontSize: '24px', color: '#6c63ff' } : {}}></i>
                                    </div>
                                    <span>{job.organisation_name || 'Company'}</span>
                                </div>
                            </li>
                            {salary ? (
                                <li><h3>{salary}</h3></li>
                            ) : (
                                <li><span style={{ color: '#aaa', fontSize: '13px' }}>Salary not listed</span></li>
                            )}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default JobCard;
