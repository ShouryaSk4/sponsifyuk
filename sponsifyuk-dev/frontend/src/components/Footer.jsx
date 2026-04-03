import React from 'react';
import { Link } from 'react-router-dom';
import $ from 'jquery';

const Footer = () => {
    return (
        <>
            <div className="footer-area bg-color pt-100 pb-70">
                <div className="container">
                    <div className="row">
                        <div className="col-lg-4 col-sm-6">
                            <div className="single-footer-widget logo-content">
                                <div className="footer-logo">
                                    <Link to="/"><img src="/assets/images/logo.jpg" alt="Logo" width="200" style={{ borderRadius: "10px" }} /></Link>
                                </div>
                                <div className="social-content">
                                    <ul>
                                        <li>
                                            <span>Follow Us:</span>
                                        </li>
                                        <li>
                                            <a href="https://www.facebook.com/" target="_blank" rel="noreferrer"><i className="fa-brands fa-facebook-f"></i></a>
                                        </li>
                                        <li>
                                            <a href="https://www.twitter.com/" target="_blank" rel="noreferrer"><i className="fa-brands fa-twitter"></i></a>
                                        </li>
                                        <li>
                                            <a href="https://instagram.com/?lang=en" target="_blank" rel="noreferrer"><i className="fa-brands fa-instagram"></i></a>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-4 col-sm-6">
                            <div className="single-footer-widget quick-link">
                                <h3>Company</h3>
                                <ul>
                                    <li><Link to="/about-us">About Us</Link></li>
                                    <li><Link to="/contact">Contact Us</Link></li>
                                    <li><Link to="/terms-conditions">Terms &amp; Conditions</Link></li>
                                    <li><Link to="/privacy-policy">Privacy Policy</Link></li>
                                </ul>
                            </div>
                        </div>
                        <div className="col-lg-4 col-sm-6">
                            <div className="single-footer-widget info">
                                <h3>Official Info</h3>
                                <ul>
                                    <li>
                                        <i className="fa-solid fa-envelope"></i>
                                        <h4>Email:</h4>
                                        <a href="mailto:support@sponsifyuk.com">support@sponsifyuk.com</a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="copy-right">
                <div className="container">
                    <p>© <span>SponsifyUK</span> is Proudly Owned by <a href="https://aztechinfoway.com/" target="_blank" rel="noreferrer">Aztech Infoway</a></p>
                </div>
            </div>

            <div className="go-top active">
                <i className="fa-solid fa-arrow-up-long"></i>
                <i className="fa-solid fa-arrow-up-long"></i>
            </div>

            <div className="modal fade in show" id="disclaimerModal" tabindex="-1" aria-hidden="true">
                <div className="modal-dialog modal-xl modal-dislog-centered">
                    <div className="modal-content">
                        <div className="modal-header text-center">
                            <h1 className="modal-title w-100">
                                <svg xmlns="http://www.w3.org/2000/svg" className="bi flex-shrink-0 me-2" viewBox="0 0 16 16" role="img" aria-label="Warning:" style={{width: '50px', height: '50px'}}>
                                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z" fill="red" />
                                </svg>
                                <br/>Disclaimer
                            </h1>
                        </div>
                        <div className="modal-body">
                            <p><strong>I understand that jobs listed on SponsifyUK do not guarantee employment or visa sponsorship. Sponsorship decisions and interview outcomes are determined solely by employers and authorities, and I proceed at my own risk.</strong></p>

                            <p>SponsifyUK aims to list roles where employers may be open to visa sponsorship; however, we do not guarantee that any job listed will result in sponsorship, employment, or an interview.</p>

                            <p>All sponsorship decisions are made solely by employers and relevant authorities. Outcomes depend on factors such as employer requirements, interview performance, eligibility, qualifications, immigration rules, and market conditions — all of which are beyond our control.</p>

                            <p>Any actions taken after viewing or applying for jobs on this website, including attending interviews, accepting offers, or engaging with employers, are done entirely at the user’s own discretion and risk. SponsifyUK is not responsible for any loss, harm, or negative outcome arising from such actions.</p>

                            <p>Users are strongly advised to independently verify job details, sponsorship eligibility, and employer authenticity before proceeding.</p>
                        </div>
                        <div className="modal-footer">
                            <label><input type="checkbox" name="AgreeTerms"/> I agree to the above terms and conditions.</label>
                            <button type="button" className="btn btn-primary" disabled>I Agree</button>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Footer;
