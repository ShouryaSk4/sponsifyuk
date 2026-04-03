/**
 * SponsifyUK — Frontend ↔ API Bridge  (assets/scripts/app.js)
 * ============================================================
 * Add ONE <script> tag at the bottom of every HTML page, AFTER
 * the existing script tags:
 *
 *   <script src="assets/scripts/app.js"></script>
 *
 * This file handles:
 *   • login.html        — Login form submission
 *   • register.html     — Register form submission
 *   • index.html        — Homepage search form
 *   • job-listing.html  — Job listing search + render results
 *   • job-details.html  — Load & populate job details
 *   • dashboard.html    — Populate user name & stats
 *   • pricing.htm       — Upgrade to premium buttons
 *   • All pages         — Nav login/logout state
 *
 * No changes needed in any HTML file. No new dependencies needed.
 */

(function ($) {
    'use strict';

    /* ================================================================
       CONFIG
    ================================================================ */
    var API = 'http://localhost:5000/api';

    /* ================================================================
       SESSION STORAGE — lightweight client-side auth state
       We store the user object in sessionStorage so nav / pages know
       who is logged in across page navigations without re-hitting the
       API every time (we still verify on the server via cookie session).
    ================================================================ */
    var Auth = {
        save: function (user) {
            try { sessionStorage.setItem('spk_user', JSON.stringify(user)); } catch (e) {}
        },
        get: function () {
            try { return JSON.parse(sessionStorage.getItem('spk_user')); } catch (e) { return null; }
        },
        clear: function () {
            try { sessionStorage.removeItem('spk_user'); } catch (e) {}
        },
        isLoggedIn: function () { return !!Auth.get(); },
        isPremium: function () { var u = Auth.get(); return u && u.is_premium; }
    };

    /* ================================================================
       UTILITIES
    ================================================================ */
    function apiPost(path, body, callback) {
        $.ajax({
            type: 'POST',
            url: API + path,
            contentType: 'application/json',
            data: JSON.stringify(body),
            xhrFields: { withCredentials: true },
            success: function (data) { callback(null, data); },
            error: function (xhr) {
                var msg = 'Request failed.';
                try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) {}
                callback(msg, null);
            }
        });
    }

    function apiGet(path, callback) {
        $.ajax({
            type: 'GET',
            url: API + path,
            xhrFields: { withCredentials: true },
            success: function (data) { callback(null, data); },
            error: function (xhr) {
                var msg = 'Request failed.';
                try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) {}
                callback(msg, null);
            }
        });
    }

    function showAlert(msg, type) {
        type = type || 'danger';
        $('#spk-alert').remove();
        var $div = $('<div id="spk-alert" role="alert">')
            .addClass('alert alert-' + type + ' alert-dismissible fade show')
            .css({
                position: 'fixed', top: '80px',
                left: '50%', transform: 'translateX(-50%)',
                zIndex: 9999, minWidth: '320px', textAlign: 'center',
                boxShadow: '0 4px 12px rgba(0,0,0,.15)'
            })
            .html(msg + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>');
        $('body').append($div);
        setTimeout(function () { $div.remove(); }, 4500);
    }

    function pageName() {
        return window.location.pathname.split('/').pop() || 'index.html';
    }

    function queryParam(name) {
        return new URLSearchParams(window.location.search).get(name) || '';
    }

    /* ================================================================
       NAV STATE — show username / logout link when logged in
    ================================================================ */
    function updateNav() {
        var user = Auth.get();

        if (user) {
            // Replace any "Login" nav links with user's first name → dashboard
            $('a[href="login.html"]').each(function () {
                $(this).text(user.first_name || user.username).attr('href', 'dashboard.html');
            });

            // Wire logout links
            $('a[href="logout.html"]').on('click', function (e) {
                e.preventDefault();
                apiPost('/users/logout', {}, function () {
                    Auth.clear();
                    window.location.href = 'index.html';
                });
            });

            // Show premium badge in nav if applicable
            if (user.is_premium) {
                $('a[href="pricing.htm"]').each(function () {
                    $(this).text('⭐ Premium').css('color', '#f7c500');
                });
            }
        }
    }

    /* ================================================================
       LOGIN FORM  (login.html)
       Inputs: #email, #password
    ================================================================ */
    function initLoginForm() {
        var $form = $('.login form');
        if (!$form.length) return;

        $form.on('submit', function (e) {
            e.preventDefault();

            var username = $('#email').val().trim();
            var password = $('#password').val();

            if (!username || !password) {
                showAlert('Please enter your email and password.');
                return;
            }

            var $btn = $form.find('button[type="submit"]');
            $btn.prop('disabled', true).text('Logging in…');

            apiPost('/users/login', { username: username, email: username, password: password },
                function (err, data) {
                    $btn.prop('disabled', false).text('Login');

                    if (err || !data.success) {
                        showAlert(err || data.error || 'Login failed. Please check your credentials.');
                        return;
                    }

                    Auth.save(data.user);
                    showAlert('Welcome back, ' + (data.user.first_name || data.user.username) + '!', 'success');
                    setTimeout(function () {
                        window.location.href = data.redirect || 'dashboard.html';
                    }, 700);
                }
            );
        });
    }

    /* ================================================================
       REGISTER FORM  (register.html)
       Inputs: #email2, #password2, #password3
    ================================================================ */
    function initRegisterForm() {
        var $form = $('.register form');
        if (!$form.length) return;

        $form.on('submit', function (e) {
            e.preventDefault();

            var email    = $('#email2').val().trim();
            var password = $('#password2').val();
            var confirm  = $('#password3').val();

            if (!email || !password) {
                showAlert('Please fill in all required fields.');
                return;
            }
            if (password !== confirm) {
                showAlert('Passwords do not match.');
                return;
            }
            if (password.length < 6) {
                showAlert('Password must be at least 6 characters.');
                return;
            }

            var $btn = $form.find('button[type="submit"]');
            $btn.prop('disabled', true).text('Creating account…');

            apiPost('/users/register',
                { email: email, username: email, password: password, confirm_password: confirm },
                function (err, data) {
                    $btn.prop('disabled', false).text('Register');

                    if (err || !data.success) {
                        showAlert(err || data.error || 'Registration failed. Please try again.');
                        return;
                    }

                    showAlert('Account created! Redirecting…', 'success');
                    setTimeout(function () {
                        window.location.href = data.redirect || 'dashboard.html';
                    }, 700);
                }
            );
        });
    }

    /* ================================================================
       DASHBOARD  (dashboard.html)
       Populates: user greeting, stats boxes, premium badge
    ================================================================ */
    function initDashboard() {
        // Check we're on dashboard
        if (!$('.breadcrumb-area h1').length) return;

        var user = Auth.get();
        if (!user) {
            window.location.href = 'login.html';
            return;
        }

        // Set greeting
        var fullName = ((user.first_name || '') + ' ' + (user.last_name || '')).trim() || user.username;
        $('.breadcrumb-area h1').text(fullName);

        // Load live stats from server
        apiGet('/users/me', function (err, data) {
            if (err || !data.success) return;

            // Update local auth store with fresh data
            Auth.save(data.user);

            var s = data.stats || {};
            // Stats boxes: [Searches, Applications, -, Saved Jobs]
            var $boxes = $('.stats-fun-fact-box h3');
            if ($boxes.eq(0).length) $boxes.eq(0).text(s.total_searches    || 0);
            if ($boxes.eq(1).length) $boxes.eq(1).text(s.total_applications || 0);
            if ($boxes.eq(3).length) $boxes.eq(3).text(s.saved_jobs        || 0);
        });

        // Premium badge
        if (user.is_premium) {
            var $badge = $('<span class="badge ms-2">')
                .css({ background: '#f7c500', color: '#000', fontSize: '0.6em',
                       verticalAlign: 'middle', borderRadius: '4px', padding: '3px 8px' })
                .text('⭐ Premium');
            $('.breadcrumb-area h1').append($badge);
        }

        // Load invoices
        apiGet('/users/' + user.user_id + '/invoices', function (err, data) {
            if (err || !data.success || !data.invoices.length) return;

            var $list = $('.invoices-box ul').empty();
            $.each(data.invoices, function (i, inv) {
                var statusClass = inv.status === 'success' ? 'paid' : 'unpaid';
                var statusLabel = inv.status === 'success' ? 'Paid' : 'Unpaid';
                var date        = inv.created_at ? inv.created_at.split('T')[0].split(' ')[0] : '';
                $list.append(
                    '<li>' +
                    '<div class="icon"><i class="fa-solid fa-file-lines"></i></div>' +
                    '<ul>' +
                    '<li class="' + statusClass + '">' + statusLabel + '</li>' +
                    '<li>Order: #' + inv.payment_id + '</li>' +
                    '<li>Date: ' + date + '</li>' +
                    '</ul>' +
                    '<span>' + inv.plan + '</span>' +
                    '<a href="#" class="default-btn btn">View Invoice</a>' +
                    '</li>'
                );
            });
        });
    }

    /* ================================================================
       JOB SEARCH — shared logic used by index.html & job-listing.html
    ================================================================ */
    function buildJobCard(job) {
        var daysAgo = '';
        if (job.dateposted) {
            var posted = new Date(job.dateposted);
            if (!isNaN(posted.getTime())) {
                var d = Math.floor((Date.now() - posted) / 86400000);
                daysAgo = d === 0 ? 'Today' : d + ' Day' + (d === 1 ? '' : 's') + ' Ago';
            }
        }
        var salary   = job.salary && job.salary !== 'Not Specified' ? job.salary : '';
        var location = job.location || job.org_location || 'UK';
        var jobType  = job.remote_type || 'Fulltime';

        return (
            '<div class="col-lg-6 col-md-6">' +
            '<div class="single-job-card">' +
            '<div class="job-content">' +
            '<div class="d-flex justify-content-between align-items-center mb-2">' +
            '<span class="time">' + jobType + '</span>' +
            (job.exists_in_uk === 0 ? '<span class="time" style="background-color: #f7c500; color: #000; margin-left: 8px;">Remote / Global Job</span>' : '') +
            '<a href="#" class="spk-bookmark" data-job-id="' + job.id + '">' +
            '<i class="fa-regular fa-bookmark" style="color:#bbb;font-size:16px;"></i>' +
            '</a>' +
            '</div>' +
            '<h2><a href="job-details.html?job_id=' + job.id + '">' + job.job_title + '</a></h2>' +
            '<div class="info"><ul>' +
            (daysAgo ? '<li><i class="flaticon-time"></i>' + daysAgo + '</li>' : '') +
            '<li><i class="flaticon-location"></i>' + location + '</li>' +
            '</ul></div>' +
            '<div class="bottom-content"><ul class="d-flex justify-content-between align-items-center">' +
            '<li><div class="left-content">' +
            '<div class="icon"><i class="fa-solid fa-building"></i></div>' +
            '<span>' + (job.organisation_name || 'Company') + '</span>' +
            '</div></li>' +
            (salary ? '<li><h3>' + salary + '</h3></li>' : '<li><span style="color:#aaa;font-size:13px;">Salary not listed</span></li>') +
            '</ul></div>' +
            '</div>' +
            '</div>' +
            '</div>'
        );
    }

    /* --- Keep track of last search so pagination can re-run it --- */
    var _lastSearch = { query: '', filters: {}, page: 1 };

    function renderPagination(data) {
        var $pag = $('.paginations ul');
        if (!$pag.length) return;

        var page       = data.page || 1;
        var totalPages = data.total_pages || 1;
        if (totalPages <= 1) { $pag.empty(); return; }

        var html = '';
        // Prev
        html += '<li><a href="#" data-page="' + Math.max(1, page - 1) + '"' +
                (page === 1 ? ' class="disabled"' : '') + '>' +
                '<i class="fa-solid fa-angle-left"></i></a></li>';

        // Page numbers (show max 5 centered around current)
        var startP = Math.max(1, page - 2);
        var endP   = Math.min(totalPages, startP + 4);
        if (endP - startP < 4) startP = Math.max(1, endP - 4);

        for (var p = startP; p <= endP; p++) {
            html += '<li><a href="#" data-page="' + p + '"' +
                    (p === page ? ' class="active"' : '') + '>' + p + '</a></li>';
        }

        // Next
        html += '<li><a href="#" data-page="' + Math.min(totalPages, page + 1) + '"' +
                (page === totalPages ? ' class="disabled"' : '') + '>' +
                '<i class="fa-solid fa-angle-right"></i></a></li>';

        $pag.html(html);

        // Click handler
        $pag.find('a').off('click').on('click', function (e) {
            e.preventDefault();
            var newPage = parseInt($(this).data('page'), 10);
            if (newPage && newPage !== page) {
                runSearch(_lastSearch.query, _lastSearch.filters, newPage);
                // Scroll to top of results
                $('html, body').animate({ scrollTop: $('.job-listing-content').offset().top - 80 }, 300);
            }
        });
    }

    function renderJobResults(data) {
        var $container = $('.job-listing-content .row.justify-content-center');
        if (!$container.length) return;

        // Update result count label
        var start = ((data.page || 1) - 1) * 10 + 1;
        var end   = Math.min(start + data.jobs.length - 1, data.total);
        $('.shoing-content span').text(
            'Showing ' + start + '-' + end + ' of ' + data.total + ' results'
        );

        if (!data.jobs.length) {
            $container.html(
                '<div class="col-12 text-center py-5">' +
                '<h4>No jobs found matching your search.</h4>' +
                '<p>Try different keywords or broaden your filters.</p>' +
                '</div>'
            );
            return;
        }

        var html = '';
        $.each(data.jobs, function (i, job) { html += buildJobCard(job); });
        $container.html(html);
        attachBookmarkListeners($container);

        // Render pagination
        renderPagination(data);
    }

    function runSearch(query, filters, page) {
        _lastSearch = { query: query, filters: filters, page: page };

        var user    = Auth.get();
        var payload = $.extend({ query: query, page: page, limit: 10 }, filters);
        if (user) payload.user_id = user.user_id;

        // Show loading state
        var $container = $('.job-listing-content .row.justify-content-center');
        $container.html(
            '<div class="col-12 text-center py-5">' +
            '<i class="fa-solid fa-spinner fa-spin fa-2x" style="color:#1d90c9;"></i>' +
            '<p class="mt-3">Searching jobs...</p>' +
            '</div>'
        );

        apiPost('/jobs/search', payload, function (err, data) {
            if (err || !data.success) {
                if (data && data.limit_reached) {
                    showAlert(
                        'Daily search limit reached. ' +
                        '<a href="pricing.htm" class="alert-link">Upgrade to Premium</a> for unlimited searches.',
                        'warning'
                    );
                } else {
                    showAlert((data && data.error) || err || 'Search failed.');
                }
                $container.html(
                    '<div class="col-12 text-center py-5">' +
                    '<h4>Search could not be completed.</h4>' +
                    '</div>'
                );
                return;
            }
            renderJobResults(data);
        });
    }

    /* ================================================================
       INDEX.HTML  — homepage search form
       Redirects to job-listing.html with query params
    ================================================================ */
    function initHomepageSearch() {
        // Only on index.html
        if (pageName() !== 'index.html' && pageName() !== '') return;

        $('.banner-search-form form').on('submit', function (e) {
            e.preventDefault();
            var keyword  = $(this).find('input[type="text"]:eq(0)').val().trim();
            var location = $(this).find('input[type="text"]:eq(1)').val().trim();
            var params   = new URLSearchParams({ q: keyword, location: location });
            window.location.href = 'job-listing.html?' + params.toString();
        });

        // Load featured jobs into any job card carousel/grid on the homepage
        apiGet('/jobs/featured?limit=6', function (err, data) {
            if (err || !data.success) return;
            var $container = $('.job-slider, .featured-jobs-container').first();
            if (!$container.length) return;
            var html = '';
            $.each(data.jobs, function (i, job) {
                // buildJobCard returns a col-lg-6 grid wrapper. Strip it for the carousel.
                var $card = $(buildJobCard(job)).find('.single-job-card');
                $card.addClass('style-2'); // Homepage uses style-2
                html += $('<div>').append($card).html();
            });
            // Inject and tell Owl Carousel to re-initialize
            if ($container.hasClass('owl-carousel')) {
                $container.trigger('replace.owl.carousel', html).trigger('refresh.owl.carousel');
            } else {
                $container.html(html);
            }
        });
    }

    /* ================================================================
       HOMEPAGE DYNAMIC CATEGORIES
    ================================================================ */
    function initHomepageCategories() {
        if (pageName() !== 'index.html' && pageName() !== '') return;
        var $target = $('#dynamic-categories-container');
        if (!$target.length) return;

        apiGet('/categories/top', function(err, data) {
            if (err || !data.success) return;
            
            var html = '';
            var delay = 200;
            $.each(data.categories, function(i, cat) {
                html += '<div class="col-lg-3 col-sm-6 aos-init aos-animate" data-aos="fade-up" data-aos-duration="1200" data-aos-delay="' + delay + '">' +
                            '<div class="single-categories-box">' +
                                '<div class="icon">' +
                                    '<i class="fa-solid ' + (cat.icon || 'fa-briefcase') + '"></i>' +
                                '</div>' +
                                '<h3>' + (cat.name || 'Other') + '</h3>' +
                                '<span>(' + cat.count + ' Open Positions)</span>' +
                            '</div>' +
                        '</div>';
                delay += 200;
            });
            $target.html(html);
        });
    }

    /* ================================================================
       JOB-LISTING.HTML  — search form + results rendering
    ================================================================ */
    function initJobListing() {
        if (!$('.job-listing-content').length) return;

        // Pre-fill form from URL params (redirect from index.html)
        var urlParams = new URLSearchParams(window.location.search);
        var q        = urlParams.get('q') || '';
        var location = urlParams.get('location') || '';
        var category = urlParams.get('category') || '';

        if (q)        $('input[placeholder*="Keywords"], input[placeholder*="Job"]').first().val(q);
        if (location) $('input[placeholder*="City"], input[placeholder*="Postcode"]').first().val(location);
        if (category) $('select.form-select').val(category);

        // Run initial search (empty query = show all / latest jobs)
        runSearch(q, { location: location, category: category }, 1);

        // Main search form submit
        $('.job-listing-search-form form').on('submit', function (e) {
            e.preventDefault();
            var keyword   = $(this).find('input[type="text"]:eq(0)').val().trim();
            var loc       = $(this).find('input[type="text"]:eq(1)').val().trim();
            var cat       = $(this).find('select').first().val() || '';
            runSearch(keyword, { location: loc, category: cat }, 1);
        });

        // Sidebar: Employment Type filter links
        $(document).on('click', '.single-sidebar-widget.range a', function (e) {
            e.preventDefault();
            var text = $(this).text().trim();

            // Map sidebar label → API value
            var remoteMap = {
                'Full Time Jobs': 'Full Time',
                'Part Time Jobs': 'Part Time',
                'Remote Jobs':    'Remote',
                'Internship':     'Internship',
                'Contract':       'Contract',
            };
            var expMap = {
                'Student Level': 'Student',
                'Entry Level':   'Entry Level',
                'Mid Level':     'Mid Level',
                'Senior level':  'Senior',
                'Directors':     'Director',
            };

            var filters = {};
            if (remoteMap[text])  filters.remote_type      = remoteMap[text];
            if (expMap[text])     filters.experience_level = expMap[text];

            var q = $('input[placeholder*="Keywords"], input[placeholder*="Job"]').first().val().trim();
            runSearch(q, filters, 1);
        });
    }

    /* ================================================================
       JOB-DETAILS.HTML  — load & populate job details
       Reads ?job_id= from the URL
    ================================================================ */
    function initJobDetails() {
        if (!$('.job-details-area').length && !$('.job-details-banner-area').length) return;

        var urlParams = new URLSearchParams(window.location.search);
        var jobId = urlParams.get('job_id');
        if (!jobId) return;

        apiGet('/jobs/' + jobId, function (err, data) {
            if (err || !data.success) {
                showAlert('Could not load job details.');
                return;
            }
            var job = data.job;

            // Banner — populate and restore colors from loading state
            var $banner = $('.job-details-banner-left-content');
            $banner.find('h2').text(job.job_title || '').css('color', '');
            $banner.find('> span').first().text(job.organisation_name || '').css('color', '');
            $banner.find('.info li').last()
                .html('<i class="flaticon-location"></i>' + (job.location || job.org_location || ''));

            // Description — handle multi-line, strip loading state
            var desc = job.job_description || 'No description available.';
            // Split into paragraphs if long
            var descHtml = desc.split(/\n\n|\r\n\r\n/).map(function(p) {
                return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
            }).join('');
            $('.job-description').html('<h3>Job Description</h3>' + descHtml);

            // Sidebar overview
            var ov = $('.job-overview li');
            function setOvItem(idx, label, val) {
                if (ov.eq(idx).length && val) ov.eq(idx).html('<span>' + label + '</span>' + val);
            }
            setOvItem(1, 'Job Type:', job.remote_type);
            setOvItem(2, 'Experience:', job.experience_level);
            setOvItem(3, 'Job Location:', job.location || job.org_location);

            // Apply Now button
            if (job.job_link) {
                var url = job.job_link;
                if (url.indexOf('@') !== -1 && url.indexOf('http') === -1 && url.indexOf('mailto:') === -1) {
                    url = 'mailto:' + url;
                }
                
                $('.job-details-banner-right-content a.default-btn')
                    .attr('href', url)
                    .attr('target', '_blank')
                    .attr('rel', 'noopener noreferrer')
                    .on('click', function () {
                        var user = Auth.get();
                        if (user) {
                            apiPost('/users/' + user.user_id + '/apply',
                                { company_name: job.organisation_name, search_keywords: job.job_title },
                                function () {}
                            );
                        }
                    });
            }

            // Bookmark button
            var $bm = $('.job-details-banner-right-content .bookmark').closest('a');
            if ($bm.length) {
                $bm.data('saved', data.job.is_saved || false);
                if (data.job.is_saved) $bm.find('.bookmark').css('color', '#f7c500');
                $bm.on('click', function (e) {
                    e.preventDefault();
                    toggleSaveJob(jobId, $(this));
                });
            }

            document.title = job.job_title + ' — SponsifyUK';
        });
    }

    /* ================================================================
       BOOKMARK / SAVE JOB
    ================================================================ */
    function toggleSaveJob(jobId, $btn) {
        var user = Auth.get();
        if (!user) { window.location.href = 'login.html'; return; }

        var isSaved = $btn.data('saved') === true || $btn.data('saved') === 'true';

        if (isSaved) {
            $.ajax({
                type: 'DELETE',
                url: API + '/users/' + user.user_id + '/saved-jobs?job_id=' + jobId,
                xhrFields: { withCredentials: true },
                success: function () {
                    $btn.data('saved', false);
                    $btn.find('.bookmark').css('color', '');
                    showAlert('Removed from saved jobs.', 'warning');
                }
            });
        } else {
            apiPost('/users/' + user.user_id + '/saved-jobs', { job_id: jobId }, function () {
                $btn.data('saved', true);
                $btn.find('.bookmark').css('color', '#f7c500');
                showAlert('Job saved!', 'success');
            });
        }
    }

    function attachBookmarkListeners($container) {
        $container.find('.spk-bookmark').on('click', function (e) {
            e.preventDefault();
            toggleSaveJob($(this).data('job-id'), $(this));
        });
    }

    /* ================================================================
       PRICING.HTM  — upgrade buttons
    ================================================================ */
    function initPricingPage() {
        if (pageName().indexOf('pricing') === -1) return;

        // Target any "Get Started" / "Choose Plan" button
        $('.pricing-box .default-btn, .plan-btn, .price-btn, .default-btn, .single-pricing-card .default-btn').filter(function () {
            var t = $(this).text().toLowerCase();
            return t.indexOf('get start') !== -1 || t.indexOf('choose') !== -1 ||
                   t.indexOf('upgrade') !== -1 || t.indexOf('buy') !== -1;
        }).on('click', function (e) {
            e.preventDefault();
            var user = Auth.get();

            if (!user) { window.location.href = 'login.html'; return; }
            if (user.is_premium) {
                showAlert('You are already a Premium member! 🎉', 'success');
                return;
            }

            // Find price from the card above the button
            var priceText = $(this).closest('.single-pricing-card').find('h1').text();
            var amount = 50; // default
            if (priceText.indexOf('£10') !== -1) amount = 10;
            if (priceText.indexOf('£25') !== -1) amount = 25;
            
            var $btn = $(this).prop('disabled', true).text('Processing…');

            apiPost('/create-checkout-session', { user_id: user.user_id, amount: amount }, function (err, data) {
                $btn.prop('disabled', false).text('Get Start Now');

                if (err) {
                    showAlert('Error creating checkout session: ' + err, 'danger');
                    return;
                }

                if (data.success && data.checkout_url) {
                    // Redirect to Stripe Hosted Checkout
                    window.location.href = data.checkout_url;
                } else if (data.already_premium) {
                    showAlert('You are already a premium member!', 'success');
                } else {
                    showAlert(data.message || 'Payment failed.', 'danger');
                }
            });
        });
    }

    /* ================================================================
       AUTOCOMPLETE — Search Suggestions
    ================================================================ */
    function initAutocomplete() {
        function setupAutocomplete(inputId, suggestionsId, type) {
            var $input = $('#' + inputId);
            var $sug_box = $('#' + suggestionsId);
            
            if (!$input.length) return;

            var timer;
            $input.on('input', function() {
                var query = $(this).val().trim();
                clearTimeout(timer);
                
                if (query.length < 2) {
                    $sug_box.hide().empty();
                    return;
                }
                
                timer = setTimeout(function() {
                    $.ajax({
                        url: API + '/jobs/suggestions?q=' + encodeURIComponent(query) + '&type=' + type,
                        type: 'GET',
                        success: function(res) {
                            $sug_box.empty();
                            if (res && res.length > 0) {
                                res.forEach(function(item) {
                                    var $div = $('<div>' + item + '</div>');
                                    $div.on('click', function() {
                                        $input.val(item);
                                        $sug_box.hide().empty();
                                    });
                                    $sug_box.append($div);
                                });
                                $sug_box.show();
                            } else {
                                $sug_box.hide();
                            }
                        }
                    });
                }, 300); // 300ms debounce
            });

            // Hide suggestions when clicking outside
            $(document).on('click', function(e) {
                if (!$(e.target).closest('.form-group.position-relative').length) {
                    $sug_box.hide();
                }
            });
        }

        setupAutocomplete('search-title', 'title-suggestions', 'title');
        setupAutocomplete('search-location', 'location-suggestions', 'location');
    }

    /* ================================================================
       DYNAMIC SITE STATISTICS 
    ================================================================ */
    function initSiteStats() {
        var $counters = $('.counters-area .odometer');
        if (!$counters.length) return;

        apiGet('/stats', function(err, data) {
            if (err || !data.success || !data.stats) return;

            // Map the API keys to the HTML layout order
            // 1. Total Jobs
            // 2. Sponsored Companies
            // 3. Live Domains
            // 4. Total Members
            var statsMap = [
                data.stats.total_jobs,
                data.stats.total_companies,
                data.stats.total_domains,
                data.stats.total_members
            ];

            $counters.each(function(index) {
                if (statsMap[index] !== undefined) {
                    var finalVal = statsMap[index];
                    // Setting data-count prevents custom.js from overwriting it back to the HTML default
                    $(this).attr('data-count', finalVal);
                    // Force the odometer library to update instantly if it already initialized
                    if ($(this).hasClass('odometer-auto-theme')) {
                        $(this).html(finalVal);
                    }
                }
            });
        });
    }

    /* ================================================================
       BOOT — run everything on DOM ready
    ================================================================ */
    $(document).ready(function () {
        updateNav();
        initLoginForm();
        initRegisterForm();
        initDashboard();
        initHomepageSearch();
        initHomepageCategories();
        initSiteStats();
        initJobListing();
        initJobDetails();
        initPricingPage();
        initAutocomplete();
    });

}(jQuery));
