// Click-to-expand for .petri-architecture-figure images.
(function () {
  'use strict';

  function activeImg(figure) {
    var imgs = figure.querySelectorAll('img');
    for (var i = 0; i < imgs.length; i++) {
      if (imgs[i].offsetParent !== null || getComputedStyle(imgs[i]).display !== 'none') {
        return imgs[i];
      }
    }
    return imgs[0];
  }

  function initFigure(figure) {
    var dialog = document.createElement('dialog');
    dialog.className = 'petri-diagram-dialog';
    dialog.innerHTML =
      '<div class="petri-diagram-dialog-inner">' +
      '<header class="petri-diagram-dialog-header">' +
      '<span>System architecture</span>' +
      '<button class="petri-diagram-dialog-close" aria-label="Close">' +
      '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">' +
      '<path d="M2 2l12 12M14 2L2 14"/>' +
      '</svg></button>' +
      '</header>' +
      '<div class="petri-diagram-dialog-body"></div>' +
      '</div>';
    document.body.appendChild(dialog);

    var dialogBody = dialog.querySelector('.petri-diagram-dialog-body');

    function open() {
      var img = activeImg(figure);
      dialogBody.innerHTML = '';
      var clone = document.createElement('img');
      clone.src = img.src;
      clone.alt = img.alt;
      clone.style.cssText = 'display:block;width:100%;height:auto;';
      dialogBody.appendChild(clone);
      dialog.showModal();
    }

    figure.addEventListener('click', open);

    dialog.querySelector('.petri-diagram-dialog-close').addEventListener('click', function () {
      dialog.close();
    });
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) dialog.close();
    });
  }

  function init() {
    document.querySelectorAll('.petri-architecture-figure').forEach(initFigure);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
