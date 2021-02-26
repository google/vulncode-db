// setup shadow dom
const treeHead = document.querySelector('#product-search');
const parent = document.createElement('div');
const holder = document.createElement('div');
const shadow = treeHead.attachShadow({mode: 'open'});
parent.appendChild(holder);
shadow.appendChild(parent);

// ##### workarounds ahead!! ####
(function() {
  // https://github.com/vuetifyjs/vuetify/issues/7622
  const {querySelector} = document;
  document.querySelector = function(selector) {
    if (selector === '[data-app]') return shadow.querySelector(selector);
    return querySelector.call(this, selector);
  };
  // ugly hack until https://github.com/vuetifyjs/vuetify/issues/7622 is fixed
  // we're not using document.activeElement at the momemt so it should be fine
  // but shouldn't be mixed with monaco just in case.
  Object.defineProperty(document, 'activeElement', {
    get() {
      return shadow.activeElement;
    },
  });
  // workaround for vuetify's click-outside hack
  document.body.addEventListener('click', (e) => {
    const target = shadow.querySelector('.v-select__selections input[type=text]');
    if (e.target === target || e.target === treeHead) return;
    const evt = new KeyboardEvent('keydown', {
      keyCode: 9, // tab,
    });
    target.dispatchEvent(evt);
  });

  // https://github.com/mdn/interactive-examples/issues/887
  const fontFaceStyle = `@font-face {
    font-family: "Material Design Icons";
    src: url("https://cdn.jsdelivr.net/npm/@mdi/font@4.x/fonts/materialdesignicons-webfont.eot?v=4.9.95");
    src: url("https://cdn.jsdelivr.net/npm/@mdi/font@4.x/fonts/materialdesignicons-webfont.eot?#iefix&v=4.9.95") format("embedded-opentype"),url("https://cdn.jsdelivr.net/npm/@mdi/font@4.x/fonts/materialdesignicons-webfont.woff2?v=4.9.95") format("woff2"),url("https://cdn.jsdelivr.net/npm/@mdi/font@4.x/fonts/materialdesignicons-webfont.woff?v=4.9.95") format("woff"),url("https://cdn.jsdelivr.net/npm/@mdi/font@4.x/fonts/materialdesignicons-webfont.ttf?v=4.9.95") format("truetype");
    font-weight: normal;
    font-style: normal;
  }`;
  // fixing min-height of v-app
  const shadowStyle = `
  .v-application--wrap {
    min-height: inherit;
  }
  `;

  if (document.adoptedStyleSheets) {
    // https://github.com/mdn/interactive-examples/issues/887 and https://bugs.chromium.org/p/chromium/issues/detail?id=336876
    const fontFaceSheet = new CSSStyleSheet();
    fontFaceSheet.replaceSync(fontFaceStyle);
    document.adoptedStyleSheets = [fontFaceSheet];
    const styles = new CSSStyleSheet();
    styles.replaceSync(shadowStyle);
    shadow.adoptedStyleSheets = [styles];
  } else {
    const fontFaceSheet = document.createElement('style');
    fontFaceSheet.textContent = fontFaceStyle;
    document.body.appendChild(fontFaceSheet);

    const styles = document.createElement('style');
    styles.textContent = shadowStyle;
    shadow.appendChild(styles);
  }
})();
// ##### workarounds done!! ####


function loadStyle(url) {
  const el = document.createElement('link');
  el.setAttribute('rel', 'stylesheet');
  el.setAttribute('type', 'text/css');
  el.setAttribute('href', url);
  parent.appendChild(el);
}

loadStyle('https://cdn.jsdelivr.net/npm/@mdi/font@4.x/css/materialdesignicons.min.css');
loadStyle('https://cdn.jsdelivr.net/npm/vuetify@2.x/dist/vuetify.min.css');

function sanitizeQueryText(val) {
  val = val.toLocaleLowerCase();
  val = val.replace(' ', '_');
  val = val.replace('-', '\\-');
  return val;
}

const ProductSearch = {
  template: '#product-search-template',

  props: {
    products: Array,
  },

  data() {
    return {
      internalProducts: this.products.slice(),
      internalItems: this.products.slice(),
      loading: false,
      search: null,
      timer: null,
    };
  },

  watch: {
    search(val) {
      val && val.length > 2 && this.querySelections(val);
    },
  },

  methods: {
    customFilter(item, queryText, itemText) {
      // Only search for the product name for now.
      const productName = item.product.toLowerCase();
      // const vendorName = item.vendor.toLowerCase();
      const searchText = sanitizeQueryText(queryText);
      return productName.indexOf(searchText) > -1;
    },

    remove(item) {
      const index = this.internalProducts.indexOf(item);
      if (index >= 0) {
        this.internalProducts.splice(index, 1);
        // propagate change
        this.$emit('change', this.internalProducts.map(this.toValue));
      }
    },

    toValue(item) {
      return `${item.vendor}#~#${item.product}`;
    },

    querySelections(v) {
      this.loading = true;
      clearTimeout(this.timer);
      this.timer = setTimeout(() => {
        $.getJSON('/product/list:' + sanitizeQueryText(v), (data) => {
          this.loading = false;
          if (!data || !data.length) {
            return;
          }
          // TODO: replace with Set?
          data.forEach((pair) =>
            this.internalItems.push({vendor: pair['vendor'], product: pair['product']}));
        });
      }, 500);
    },

    escapeHTML(html) {
      const n = document.createTextNode(html);
      const p = document.createElement('pre');
      p.appendChild(n);
      return p.innerHTML.replace('"', '&quot;').replace('\'', '&#39;');
    },

    formatProductText(val) {
      if (!val || !val.length) {
        return '';
      }
      val = val.replace('\\-', '-');
      val = val.replace('_', ' ');
      val = val.charAt(0).toUpperCase() + val.slice(1);
      return val;
    },

    highlightText(text) {
      const searchInput = (this.search || '').toString().toLocaleLowerCase();
      const index = text.toLocaleLowerCase().indexOf(searchInput);

      if (index < 0) return this.escapeHTML(text);

      const start = text.slice(0, index);
      const middle = text.slice(index, index + searchInput.length);
      const end = text.slice(index + searchInput.length);

      return this.escapeHTML(start) + `<span class="v-list-item__mask">${this.escapeHTML(middle)}</span>` + this.escapeHTML(end);
    },
  },
  delimiters: ['[[', ']]'],
};


// also accessed outside of this file
let selectedProducts = [];

// hook form submit
let el = treeHead;
while (el) {
  if (el.tagName === 'FORM') {
    el.addEventListener('submit', function() {
      const container = this.querySelector('#product-fields');
      // clear node
      while (container.firstChild) {
        container.removeChild(container.lastChild);
      }
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'products';
      input.value = JSON.stringify(selectedProducts);
      container.appendChild(input);
      return false;
    });
    break;
  }
  el = el.parentElement;
}
