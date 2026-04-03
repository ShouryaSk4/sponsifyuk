/*==============================================================*/
// Contact Form JS  — updated URL to point to Flask API
// Original: assets/php/form-process.php
// Updated:  http://localhost:5000/api/contact
/*==============================================================*/
(function ($) {
    "use strict";

    $("#contactForm").validator().on("submit", function (event) {
        if (event.isDefaultPrevented()) {
            formError();
            submitMSG(false, "Did you fill in the form properly?");
        } else {
            event.preventDefault();
            submitForm();
        }
    });

    function submitForm() {
        var name         = $("#name").val();
        var email        = $("#email").val();
        var msg_subject  = $("#msg_subject").val();
        var phone_number = $("#phone_number").val();
        var message      = $("#message").val();
        var gridCheck    = $("#gridCheck").val();

        $.ajax({
            type: "POST",
            url:  "http://localhost:5000/api/contact",   // ← changed from assets/php/form-process.php
            data: {
                name:         name,
                email:        email,
                msg_subject:  msg_subject,
                phone_number: phone_number,
                message:      message,
                gridCheck:    gridCheck
            },
            success: function (statustxt) {
                if (statustxt === "success") {
                    formSuccess();
                } else {
                    formError();
                    submitMSG(false, statustxt);
                }
            },
            error: function () {
                formError();
                submitMSG(false, "Could not send message. Please try again.");
            }
        });
    }

    function formSuccess() {
        $("#contactForm")[0].reset();
        submitMSG(true, "Message Submitted!");
    }

    function formError() {
        $("#contactForm").removeClass().addClass("shake animated").one(
            "webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend",
            function () { $(this).removeClass(); }
        );
    }

    function submitMSG(valid, msg) {
        var msgClasses = valid ? "h4 tada animated text-success" : "h4 text-danger";
        $("#msgSubmit").removeClass().addClass(msgClasses).text(msg);
    }

}(jQuery));
