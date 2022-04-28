{
  ('use strict');

  const setDimensions = (el, dimensions) => {
    el.classList.remove('lazyloading');
    const dimensionsEl = el.parentElement.parentElement.querySelector('.image-dimensions');
    dimensionsEl.textContent = dimensions;
  };

  document.querySelectorAll('.lazy.lazyloading').forEach((el) => {
    console.log(el);
    if (el.localName === 'video') {
      if (el.videoWidth) {
        setDimensions(el, `${el.videoWidth}x${el.videoHeight}`);
      }
      el.addEventListener('loadeddata', (event) => {
        setDimensions(el, `${el.videoWidth}x${el.videoHeight}`);
      });
    } else {
      if (el.naturalWidth) {
        setDimensions(el, `${el.naturalWidth}x${el.naturalHeight}`);
      }
      el.addEventListener('load', (event) => {
        setDimensions(el, `${el.naturalWidth}x${el.naturalHeight}`);
      });
    }
  });

  function removeChildren(element) {
    while (element.lastChild) {
      element.removeChild(element.lastChild);
    }
  }

  const setCurrentImage = (() => {
    const imageLocal = document.getElementById('image-local');
    const imageUrl = document.getElementById('image-url');
    const imageIdEl = document.getElementById('image-id');
    const imageDeleteBtn = document.getElementById('delete-image-btn');
    const imageForm = document.getElementById('image-form');
    const imageGroup = document.getElementById('image-group-list');
    const tagsList = document.getElementById('tags-list');

    let currentImage;

    const handleClickEvent = (event) => {
      currentImage.classList.remove('col-10');
      currentImage.classList.remove('selected');
      currentImage.removeEventListener('click', handleClickEvent);
      imageDeleteBtn.disabled = true;
    };

    const handleDeleteClickEvent = (event) => {
      const imageId = imageDeleteBtn.value;
      if (confirm(`Are you sure you want to delete ${imageId}`)) {
        fetch(`/image/${imageId}`, { method: 'DELETE' }).then((res) => {
          currentImage.parentElement.removeChild(currentImage);
          imageDeleteBtn.removeEventListener('click', handleDeleteClickEvent);
          imageDeleteBtn.disabled = true;
        });
      }
    };

    imageGroup.addEventListener('change', (event) => {
      if (!currentImage) {
        return true;
      }

      const $currentImage = currentImage;

      const group = event.target;
      const groupText = group[group.selectedIndex].textContent;

      const params = new URLSearchParams();
      params.set('ig', group.value);

      fetch(`/image/${imageIdEl.textContent}`, {
        method: 'PUT',
        body: params,
      }).then(() => {
        $currentImage.dataset.group = params.get('ig');
        $currentImage.parentElement.querySelector('.image-group-text').textContent = groupText;
      });
    });

    return (imageContainer) => {
      if (currentImage) {
        currentImage.classList.remove('col-10');
        currentImage.classList.remove('selected');
      }
      currentImage = imageContainer;
      currentImage.classList.add('col-10');
      currentImage.classList.add('selected');
      console.log(currentImage);

      const mainImg = currentImage.querySelector('.image-main');
      const imageId = mainImg.dataset.id;
      imageIdEl.textContent = imageId;

      imageUrl.href = mainImg.dataset['original-link'];

      const actualSource = mainImg.querySelector('img') ?? mainImg.querySelector('source');
      imageLocal.href = actualSource.src;
      const pathComponents = actualSource.src.split('/');
      imageLocal.textContent = pathComponents[pathComponents.length - 1];

      imageGroup.value = mainImg.dataset.group;

      removeChildren(tagsList);

      const tags = mainImg.title.split(' ');
      tags.forEach((tag) => {
        const el = document.createElement('li');
        el.textContent = tag;

        tagsList.appendChild(el);
      });

      currentImage.addEventListener('click', handleClickEvent);

      imageDeleteBtn.value = imageId;
      imageDeleteBtn.disabled = false;
      imageDeleteBtn.addEventListener('click', handleDeleteClickEvent);
    };
  })();

  document.querySelectorAll('.results .image').forEach((image) => {
    image.addEventListener('click', (event) => {
      setCurrentImage(image);
    });
  });

  document.querySelectorAll('.btn > [type="checkbox"]').forEach((element) => {
    element.addEventListener('change', (event) => {
      event.target.parentElement.classList.toggle('active');
    });
  });

  const imageGroups = (() => {
    const g = localStorage.getItem('selectedGroups');
    if (g) {
      return g.split(',');
    }
    return [];
  })();

  const searchForm = document.getElementById('search-form');

  searchForm.querySelectorAll('.image-group').forEach((group) => {
    group.checked = imageGroups.includes(group.value);
    if (group.checked) {
      group.parentElement.classList.add('active');
    }
  });

  searchForm.addEventListener('submit', (event) => {
    const selected = [];
    event.target.querySelectorAll('.image-group').forEach((group) => {
      if (group.checked) {
        selected.push(group.value);
      }
    });

    localStorage.setItem('selectedGroups', selected);
  });

  const imageSidebar = document.getElementById('image-sidebar');
  const sidebarPositionFromTop = window.scrollY + imageSidebar.getBoundingClientRect().y;

  //*/
  function handleScrollEvent(lastScrollPosition) {
    const diff = lastScrollPosition - sidebarPositionFromTop;
    if (diff > 15) {
      imageSidebar.classList.add('image-sidebar__fixed');
    } else if (diff < -15) {
      imageSidebar.classList.remove('image-sidebar__fixed');
    }
  }

  handleScrollEvent(window.scrollY);

  window.addEventListener(
    'scroll',
    (event) => {
      let ticking = false;

      if (!ticking) {
        window.requestAnimationFrame(() => {
          handleScrollEvent(window.scrollY);
          ticking = false;
        });

        ticking = true;
      }
    },
    { passive: true },
  );
  /*/

  const intersection = new IntersectionObserver(
    entries => {
      if (entries[0].isIntersecting) {
        entries[0].target.classList.add('image-sidebar__fixed');
      } else {
        entries[0].target.classList.remove('image-sidebar__fixed');
      }
    },
    {
      threshold: 0,
      rootMargin: `0px 0px ${-window.innerHeight + 1}px 0px`,
    },
  );

  intersection.observe(imageSidebar);
  //*/
}
