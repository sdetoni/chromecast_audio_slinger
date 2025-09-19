class Slider
{
    constructor (mySlidesClass, idx)
    {
        this.slideIndex = idx;
        this.mySlidesClass = mySlidesClass;
    }

    // Next/previous controls
    incDecSlide(n)
    {
        this.slideIndex += n
        this.show(this.slideIndex);
    }

    // Thumbnail image controls
    thisSlide(n)
    {
        this.slideIndex = n
        this.show(this.slideIndex);
    }

    show (n)
    {
        let i;
        let slides = document.getElementsByClassName(this.mySlidesClass);
        let dots = document.getElementsByClassName("slider-dot");

        if (n > slides.length) {this.slideIndex = 1}
        if (n < 1) {this.slideIndex = slides.length}

        for (i = 0; i < slides.length; i++)
            slides[i].style.display = "none";

        for (i = 0; i < dots.length; i++)
            dots[i].className = dots[i].className.replace(" slider-active", "");

        slides[this.slideIndex-1].style.display = "block";

        dots[this.slideIndex-1].className += " slider-active";

        let imgs = slides[this.slideIndex-1].getElementsByTagName("img")
        for (i = 0; i < imgs.length; i++)
            imgs[i].style.transform = "none";

        let zoomers = document.getElementsByClassName("slider-zoom")
        for (i = 0; i < zoomers.length; i++)
        {
            zoomers[i].value = "1";
            zoomers[i].change();
            // zoomers[i].dispatchEvent(new Event("change"););
        }
    }
}
// Example.
//let slideIndex = 1;
//SliderShowSlides(slideIndex, "mySlides");
