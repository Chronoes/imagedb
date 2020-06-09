(() => {
  'use strict';

  const lazyload = new LazyLoad({
    threshold: 100,
    callback_load(image) {
      image.classList.remove('lazyloading');
      const dimensions = image.parentElement.querySelector('.image-dimensions');
      dimensions.textContent = `${image.naturalWidth}x${image.naturalHeight}`;
    },
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

    const handleClickEvent = event => {
      event.target.parentElement.classList.remove('col-10');
      event.target.parentElement.classList.remove('selected');
      event.target.removeEventListener('click', handleClickEvent);
      imageDeleteBtn.disabled = true;
    };

    let currentImage;

    const handleDeleteClickEvent = event => {
      const target = event.target;
      const imageId = event.target.value;
      if (confirm(`Are you sure you want to delete image ${imageId}`)) {
        fetch(`/image/${imageId}`, { method: 'DELETE' }).then(res => {
          // currentImage.parentElement.classList.remove('col-10');
          // currentImage.parentElement.classList.remove('selected');
          currentImage.parentElement.parentElement.removeChild(currentImage.parentElement);
          target.removeEventListener('click', handleDeleteClickEvent);
          target.disabled = true;
        });
      }
    };

    imageGroup.addEventListener('change', event => {
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
        $currentImage.setAttribute('data-group', params.get('ig'));
        $currentImage.parentElement.querySelector('.image-group-text').textContent = groupText;
      });
    });

    return image => {
      if (currentImage) {
        currentImage.parentElement.classList.remove('col-10');
        currentImage.parentElement.classList.remove('selected');
      }
      currentImage = image;
      currentImage.parentElement.classList.add('col-10');
      currentImage.parentElement.classList.add('selected');

      const imageId = parseInt(image.getAttribute('data-id'), 10);
      imageIdEl.textContent = imageId;

      imageUrl.href = image.getAttribute('data-original-link');

      imageLocal.setAttribute('href', image.src);
      const pathComponents = image.src.split('/');
      imageLocal.textContent = pathComponents[pathComponents.length - 1];

      imageGroup.value = image.getAttribute('data-group');

      removeChildren(tagsList);

      const tags = image.getAttribute('alt').split(' ');
      tags.forEach(tag => {
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

  document.querySelectorAll('.results .image img').forEach(image => {
    image.addEventListener('click', event => {
      const image = event.target;
      setCurrentImage(image);
    });
  });

  document.querySelectorAll('.btn > [type="checkbox"]').forEach(element => {
    element.addEventListener('change', event => {
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

  searchForm.querySelectorAll('.image-group').forEach(group => {
    group.checked = imageGroups.includes(group.value);
    if (group.checked) {
      group.parentElement.classList.add('active');
    }
  });

  searchForm.addEventListener('submit', event => {
    const selected = [];
    event.target.querySelectorAll('.image-group').forEach(group => {
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
    if (lastScrollPosition >= sidebarPositionFromTop) {
      imageSidebar.classList.add('image-sidebar__fixed');
    } else {
      imageSidebar.classList.remove('image-sidebar__fixed');
    }
  }

  handleScrollEvent(window.scrollY);

  window.addEventListener(
    'scroll',
    event => {
      const lastScrollPosition = window.scrollY;
      let ticking = false;

      if (!ticking) {
        window.requestAnimationFrame(() => {
          handleScrollEvent(lastScrollPosition);
          ticking = false;
        });

        ticking = true;
      }
    },
    { passive: true },
  );
  /*/
  console.log(sidebarPositionFromTop);

  const releaseIntersection = new IntersectionObserver((entries, obs) => {
    console.log('release', entries);
    obs.unobserve(entries[0].target);
  }, {
      threshold: 0,
      root: imageSidebar.parentElement,
      rootMargin: `0px 0px ${-imageSidebar.parentElement.clientHeight + 1}px 0px`
    });

  const intersection = new IntersectionObserver(entries => {
    console.log('add', entries);

    if (entries[0].isIntersecting) {
      entries[0].target.classList.add('image-sidebar__fixed');

      releaseIntersection.observe(entries[0].target);
    } else {
      // entries[0].target.classList.remove('image-sidebar__fixed');
    }
  }, {
      threshold: 0,
      rootMargin: `0px 0px ${-window.innerHeight + 1}px 0px`
    });

  intersection.observe(imageSidebar);
  /*/
})();
