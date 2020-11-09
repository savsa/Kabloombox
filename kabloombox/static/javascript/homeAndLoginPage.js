$(document).ready(function() {

    $('#logout').click(function() {
        $.post('/logout', function() {
            location.reload(true);
        });
    });


    /*Dropdown Menu*/
    $('.dropdown').click(function () {
        $(this).attr('tabindex', 1).focus();
        $(this).toggleClass('active');
        $(this).find('.dropdown-menu').slideToggle(300);
        // $('#arrow').rotate({ endDeg:180, persist:true });

        $('#arrow').animate({ deg: 180 }, {
            duration: 70,
            step: function(now) {
                $(this).css({ transform: 'rotate(' + now + 'deg)' });
            }
        });

    });

    $('.dropdown').focusout(function () {
        $('.dropdown').removeClass('active');
        $('.dropdown').find('.dropdown-menu').slideUp(300);

        $('#arrow').animate({ deg: 360 }, {
            duration: 70,
            step: function(now) {
                $(this).css({ transform: 'rotate(' + now + 'deg)' });
            }
        });
    });


});




