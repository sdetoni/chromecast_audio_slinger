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

      for (i = 0; i < slides.length; i++) {
        slides[i].style.display = "none";
      }
      for (i = 0; i < dots.length; i++) {
        dots[i].className = dots[i].className.replace(" slider-active", "");
      }
      slides[this.slideIndex-1].style.display = "block";
      dots[this.slideIndex-1].className += " slider-active";
    }
}
// Example.
//let slideIndex = 1;
//SliderShowSlides(slideIndex, "mySlides");
