(function($) {

	'use strict';
	// Mean Menu
	$('.mean-menu').meanmenu({
		meanScreenWidth: "991"
	});

	// Sticky, Go To Top JS
	$(window).on('scroll', function() {
		// Header Sticky JS
		if ($(this).scrollTop() >200){  
			$('.navbar-area').addClass("is-sticky");
		}
		else{
			$('.navbar-area').removeClass("is-sticky");
		};
	});

    $(window).on('load', function() {
        $('#disclaimerModal').modal('show');
    });

    // PRE LOADER
    $(window).on('load',function(){
        var preload=$('.ctn-preloader');
        if(preload.length>0){
        preload.delay(800).fadeOut('slow');
    }})

    // Progress Bar
	if($('.progress-line').length){
		$('.progress-line').appear(function(){
			var el = $(this);
			var percent = el.data('width');
			$(el).css('width',percent+'%');
		},{accY: 0});
	}
	if($('.count-box').length){
		$('.count-box').appear(function(){
			var $t = $(this),
				n = $t.find(".count-text").attr("data-stop"),
				r = parseInt($t.find(".count-text").attr("data-speed"), 10);

			if (!$t.hasClass("counted")) {
				$t.addClass("counted");
				$({
					countNum: $t.find(".count-text").text()
				}).animate({
					countNum: n
				}, {
					duration: r,
					easing: "linear",
					step: function() {
						$t.find(".count-text").text(Math.floor(this.countNum));
					},
					complete: function() {
						$t.find(".count-text").text(this.countNum);
					}
				});
			}
			
		},{accY: 0});
	}

	// Odometer js
    $('.odometer').appear(function(e) {
        var odo = $(".odometer");
        odo.each(function() {
            var countNumber = $(this).attr("data-count");
            $(this).html(countNumber);
        });
    });

    // AOS animation
    AOS.init({
        once: true,
        disable: function() {
        var maxWidth = 900;
        return window.innerWidth < maxWidth;
        }
    });

	// Others Option For Responsive JS 
	$(".others-option-for-responsive .dot-menu").on("click", function(){
		$(".others-option-for-responsive .container .container").toggleClass("active");
	});

    // portfolio Slider
    $('.category-slider').owlCarousel({
        loop:true,
        margin:20,
        nav:true,
        dots:false,
        thumbs: false,
        thumbsPrerendered: false,
        items:2,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        navText: [
            '<i class="flaticon-back-arrow"></i>', 
            '<i class="flaticon-right-arrows"></i>',   
        ],
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:2, 
            },
            768:{
                items:3,
            },
            992:{
                items:4,
            },
            1200:{
                items:4,
            },
                
        }
    });

    // Reviews Slider
    $('.reviews-slider').owlCarousel({
        loop:true,
        margin:20,
        nav:true,
        dots:false,
        thumbs: false,
        thumbsPrerendered: false,
        items:2,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        navText: [
            '<i class="flaticon-back-arrow"></i>', 
            '<i class="flaticon-right-arrows"></i>',   
        ],
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:1, 
            },
            768:{
                items:2,
            },
            992:{
                items:3,
            },
            1200:{
                items:3,
            },
                
        }
    });

    // Reviews Slider2
    $('.reviews-slider2').owlCarousel({
        loop:true,
        margin:20,
        nav:true,
        dots:false,
        thumbs: false,
        thumbsPrerendered: false,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        navText: [
            '<i class="flaticon-back-arrow"></i>', 
            '<i class="flaticon-right-arrows"></i>',   
        ],
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:1, 
            },
            768:{
                items:2,
            },
            992:{
                items:3,
            },
            1200:{
                items:3,
            },
                
        }
    });

    // Reviews Slider3
    $('.reviews-slider3').owlCarousel({
        loop:true,
        margin:20,
        nav:false,
        dots:true,
        thumbs: false,
        thumbsPrerendered: false,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:1, 
            },
            768:{
                items:2,
            },
            992:{
                items:2,
            },
            1200:{
                items:2,
            },
                
        }
    });

    // Location Slider
    $('.job-location-slider').owlCarousel({
        loop:true,
        margin:20,
        nav:true,
        dots:false,
        thumbs: false,
        thumbsPrerendered: false,
        items:2,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        navText: [
            '<i class="flaticon-back-arrow"></i>', 
            '<i class="flaticon-right-arrows"></i>',   
        ],
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:2, 
            },
            768:{
                items:3,
            },
            992:{
                items:4,
            },
            1200:{
                items:4,
            },
                
        }
    });

    // Location Slider
    $('.job-location-slider2').owlCarousel({
        loop:true,
        margin:20,
        nav:false,
        dots:true,
        thumbs: false,
        thumbsPrerendered: false,
        items:2,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:2, 
            },
            768:{
                items:3,
            },
            992:{
                items:4,
            },
            1200:{
                items:4,
            },
                
        }
    });

    // Partner Slider
    $('.partner-slider').owlCarousel({
        loop:true,
        margin:20,
        nav:false,
        dots:false,
        thumbs: false,
        thumbsPrerendered: false,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        responsive:{
            0:{
                items:2, 
            },
            576:{
                items:3, 
            },
            768:{
                items:4,
            },
            992:{
                items:6,
            },
            1200:{
                items:6,
            },
                
        }
    });

    // Categories Slider
    $('.categories-slider2').owlCarousel({
        loop:true,
        margin:15,
        nav:true,
        dots:false,
        thumbs: false,
        thumbsPrerendered: false,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        navText: [
            '<i class="fa-solid fa-arrow-left-long"></i>', 
            '<i class="fa-solid fa-arrow-right-long"></i>',   
        ],
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:2, 
            },
            768:{
                items:3,
            },
            992:{
                items:4,
            },
            1200:{
                items:4,
            },
                
        }
    });

    // Job Slider
    $('.job-slider').owlCarousel({
        loop:true,
        margin:20,
        nav:true,
        dots:true,
        thumbs: false,
        thumbsPrerendered: false,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        navText: [
            '<i class="fa-solid fa-arrow-left-long"></i>', 
            '<i class="fa-solid fa-arrow-right-long"></i>',   
        ],
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:1, 
            },
            768:{
                items:2,
            },
            992:{
                items:3,
            },
            1200:{
                items:3,
            },
                
        }
    });

    // Job Slider2
    $('.job-slider2').owlCarousel({
        loop:true,
        margin:20,
        nav:false,
        dots:true,
        thumbs: false,
        thumbsPrerendered: false,
        autoplay:true,
        smartSpeed: 1000,
        autoplayHoverPause:true,
        responsive:{
            0:{
                items:1, 
            },
            576:{
                items:1, 
            },
            768:{
                items:2,
            },
            992:{
                items:3,
            },
            1200:{
                items:3,
            },
                
        }
    });

	// Magnific popup
	$(document).ready(function() {
        $('.popup-youtube, .popup-vimeo, .popup-gmaps').magnificPopup({
            disableOn: 100,
            type: 'iframe',
            mainClass: 'mfp-fade',
            removalDelay: 160,
            preloader: false,
            fixedContentPos: false
        });
    });

    $('.popup-gallery').magnificPopup({
		delegate: 'a',
		type: 'image',
		tLoading: 'Loading image #%curr%...',
		mainClass: 'mfp-img-mobile',
		gallery: {
			enabled: true,
			navigateByImgClick: true,
			preload: [0,1] 
		},
		image: {
			tError: '<a href="%url%">The image #%curr%</a> could not be loaded.',
			titleSrc: function(item) {
				return item.el.attr('title') + '<small>by Marsel Van Oosten</small>';
			}
		}
	});
    // Progress Bar JS
    $('.circlechart').circlechart();

    // MixItUp JS
    try {
        var mixer = mixitup('#Container', {
            controls: {
                toggleDefault: 'none'
            }
        });
    } catch (err) {}

    // Pricing Switcher
	let el = document.getElementById('filt-monthly');
	if(el){
		let e = document.getElementById("filt-monthly"),
		d = document.getElementById("filt-yearly"),
		t = document.getElementById("switcher"),
		m = document.getElementById("monthly"),
		y = document.getElementById("yearly");
		e.addEventListener("click", function(){
			t.checked = false;
			e.classList.add("toggler--is-active");
			d.classList.remove("toggler--is-active");
			m.classList.remove("hide");
			y.classList.add("hide");
		});
		d.addEventListener("click", function(){
			t.checked = true;
			d.classList.add("toggler--is-active");
			e.classList.remove("toggler--is-active");
			m.classList.add("hide");
			y.classList.remove("hide");
		});
		t.addEventListener("click", function(){
			d.classList.toggle("toggler--is-active");
			e.classList.toggle("toggler--is-active");
			m.classList.toggle("hide");
			y.classList.toggle("hide");
		});
	}

    // Tabs
    $('.tab-menu li a').on('click', function() {
        var target = $(this).attr('data-rel');
    $('.tab-menu li a').removeClass('active');
        $(this).addClass('active');
        $("#"+target).fadeIn('slow').siblings(".tab-box").hide();
        return false;
    });

	// Subscribe form JS
    $(".newsletter-form").validator().on("submit", function (event) {
        if (event.isDefaultPrevented()) {
        // handle the invalid form...
            formErrorSub();
            submitMSGSub(false, "Please enter your email correctly.");
        } else {
            // everything looks good!
            event.preventDefault();
        }
    });
    function callbackFunction (resp) {
        if (resp.result === "success") {
            formSuccessSub();
        }
        else {
            formErrorSub();
        }
    }
    function formSuccessSub() {
        $(".newsletter-form")[0].reset();
        submitMSGSub(true, "Thank you for subscribing!");
        setTimeout(function() {
            $("#validator-newsletter, #validator-newsletter-2").addClass('hide');
        }, 4000)
    }
    function formErrorSub() {
        $(".newsletter-form").addClass("animated shake");
        setTimeout(function() {
            $(".newsletter-form").removeClass("animated shake");
        }, 1000)
    }
    function submitMSGSub(valid, msg) {
        if(valid){
            var msgClasses = "validation-success";
        } else {
            var msgClasses = "validation-danger";
        }
        $("#validator-newsletter, #validator-newsletter-2").removeClass().addClass(msgClasses).text(msg);
    }

    // Progress Bar
	if($('.progress-line').length){
		$('.progress-line').appear(function(){
			var el = $(this);
			var percent = el.data('width');
			$(el).css('width',percent+'%');
		},{accY: 0});
	}
	if($('.count-box').length) {
		$('.count-box').appear(function(){
			var $t = $(this),
				n = $t.find(".count-text").attr("data-stop"),
				r = parseInt($t.find(".count-text").attr("data-speed"), 10);

			if (!$t.hasClass("counted")) {
				$t.addClass("counted");
				$({
					countNum: $t.find(".count-text").text()
				}).animate({
					countNum: n
				}, {
					duration: r,
					easing: "linear",
					step: function() {
						$t.find(".count-text").text(Math.floor(this.countNum));
					},
					complete: function() {
						$t.find(".count-text").text(this.countNum);
					}
				});
			}
			
		},{accY: 0});
	}
    
    // FAQ Accordion
	$('.accordion').find('.accordion-title').on('click', function(){
		$(this).toggleClass('active');
		$(this).next().slideToggle('fast');
		$('.accordion-content').not($(this).next()).slideUp('fast');
		$('.accordion-title').not($(this)).removeClass('active');		
	});

    // Input Plus & Minus Number JS
    $('.input-counter').each(function() {
        var spinner = jQuery(this),
        input = spinner.find('input[type="text"]'),
        btnUp = spinner.find('.plus-btn'),
        btnDown = spinner.find('.minus-btn'),
        min = input.attr('min'),
        max = input.attr('max');
        
        btnUp.on('click', function() {
            var oldValue = parseFloat(input.val());
            if (oldValue >= max) {
                var newVal = oldValue;
            } else {
                var newVal = oldValue + 1;
            }
            spinner.find("input").val(newVal);
            spinner.find("input").trigger("change");
        });
        btnDown.on('click', function() {
            var oldValue = parseFloat(input.val());
            if (oldValue <= min) {
                var newVal = oldValue;
            } else {
                var newVal = oldValue - 1;
            }
            spinner.find("input").val(newVal);
            spinner.find("input").trigger("change");
        });
    });

    // Range Slider
	if($('.range-slider-area').length){
		$( ".range-slider-area .range-slider" ).slider({
			range: true,
			min: 1900,
			max: 2030,
			values: [ 1923, 2023 ],
			slide: function( event, ui ) {
			$( ".range-slider-area .count" ).text( ui.values[ 0 ] + " - " + ui.values[ 1 ] );
			}
		});
		
		$( ".range-slider-area .count" ).text( $( ".range-slider" ).slider( "values", 0 ) + " - " + $( ".range-slider" ).slider( "values", 1 ) );	
	}

    // Range Slider
	if($('.area-range-slider').length){
		$( ".area-range-slider" ).slider({
			range: true,
			min: 0,
			max: 100,
			values: [ 0, 50 ],
			slide: function( event, ui ) {
			$( ".area-amount" ).text( ui.values[ 1 ] );
			}
		});
		
		$( ".area-amount" ).text( $( ".area-range-slider" ).slider( "values", 1 ));	
	}

    // Metis Menu JS
	$(function () {
		$('#sidemenu-nav').metisMenu();
	});

	// Burger Menu JS
	$('.burger-menu').on('click', function() {
		$(this).toggleClass('active');
		$('.main-content').toggleClass('hide-sidemenu-area');
		$('.sidemenu-area').toggleClass('toggle-sidemenu-area');
		$('.top-navbar').toggleClass('toggle-navbar-area');
	});
	$('.responsive-burger-menu').on('click', function() {
		$('.responsive-burger-menu').toggleClass('active');
		$('.sidemenu-area').toggleClass('active-sidemenu-area');
	});

    // Year
    try {
        document.getElementById("year").innerHTML = new Date().getFullYear();
    } catch (err) {}

    // tooltip
	$(function () {
		$('[data-bs-toggle="tooltip"]').tooltip()
	});
    
	// Count Time 
	function makeTimer() {
		var endTime = new Date("September 20, 2030 17:00:00 PDT");
		var endTime = (Date.parse(endTime)) / 1000;
		var now = new Date();
		var now = (Date.parse(now) / 1000);
		var timeLeft = endTime - now;
		var days = Math.floor(timeLeft / 86400); 
		var hours = Math.floor((timeLeft - (days * 86400)) / 3600);
		var minutes = Math.floor((timeLeft - (days * 86400) - (hours * 3600 )) / 60);
		var seconds = Math.floor((timeLeft - (days * 86400) - (hours * 3600) - (minutes * 60)));
		if (hours < "10") { hours = "0" + hours; }
		if (minutes < "10") { minutes = "0" + minutes; }
		if (seconds < "10") { seconds = "0" + seconds; }
		$("#days").html(days + "<span>Days</span>");
		$("#hours").html(hours + "<span>Hours</span>");
		$("#minutes").html(minutes + "<span>Minutes</span>");
		$("#seconds").html(seconds + "<span>Seconds</span>");
	}
	setInterval(function() { makeTimer(); }, 0);

    // AJAX MailChimp JS
    $(".newsletter-form").ajaxChimp({
        url: "https://hibootstrap.us20.list-manage.com/subscribe/post?u=60e1ffe2e8a68ce1204cd39a5&amp;id=42d6d188d9", // Your url MailChimp
        callback: callbackFunction
    });

	// Go to Top
    $(window).on('scroll', function(){
        var scrolled = $(window).scrollTop();
        if (scrolled > 300) $('.go-top').addClass('active');
        if (scrolled < 300) $('.go-top').removeClass('active');
        });
    // Click Event
    $('.go-top').on('click', function() {
    $("html, body").animate({ scrollTop: "0" },  500);
    });

    // 11. Mouse Custom Cursor
    function itCursor() {
        var myCursor = jQuery(".mouseCursor");
        if (myCursor.length) {
            if ($("body")) {
                const e = document.querySelector(".cursor-inner"),
                    t = document.querySelector(".cursor-outer");
                let n,
                    i = 0,
                    o = !1;
                (window.onmousemove = function(s) {
                    o ||
                        (t.style.transform =
                            "translate(" + s.clientX + "px, " + s.clientY + "px)"),
                        (e.style.transform =
                            "translate(" + s.clientX + "px, " + s.clientY + "px)"),
                        (n = s.clientY),
                        (i = s.clientX);
                }),
                $("body").on("mouseenter", "button, a, .cursor-pointer", function() {
                        e.classList.add("cursor-hover"), t.classList.add("cursor-hover");
                    }),
                    $("body").on("mouseleave", "button, a, .cursor-pointer", function() {
                        ($(this).is("a", "button") &&
                            $(this).closest(".cursor-pointer").length) ||
                        (e.classList.remove("cursor-hover"),
                            t.classList.remove("cursor-hover"));
                    }),
                    (e.style.visibility = "visible"),
                    (t.style.visibility = "visible");
            }
        }
    }
    itCursor();
    $(".tp-cursor-point-area").on("mouseenter", function () {
		$(".mouseCursor").addClass("cursor-big");
	});

	$(".tp-cursor-point-area").on("mouseleave", function () {
		$(".mouseCursor").removeClass("cursor-big");
	});
	$(".tp-cursor-point-area").on("mouseleave", function () {
		$(".mouseCursor").removeClass("cursor-big");
	});
    
    
})(jQuery);
try {
    // function to set a given theme/color-scheme
    function setTheme(themeName) {
        localStorage.setItem('jaba_theme', themeName);
        document.documentElement.className = themeName;
    }
    // function to toggle between light and dark theme
    function toggleTheme() {
        if (localStorage.getItem('jaba_theme') === 'theme-dark') {
            setTheme('theme-light');
        } else {
            setTheme('theme-dark');
        }
    }
    // Immediately invoked function to set the theme on initial load
    (function () {
        if (localStorage.getItem('jaba_theme') === 'theme-dark') {
            setTheme('theme-dark');
            document.getElementById('slider').checked = false;
        } else {
            setTheme('theme-light');
        document.getElementById('slider').checked = true;
        }
    })();
} catch (err) {}