(function() {
  if (window.__nemtBridgeLoaded) return;
  window.__nemtBridgeLoaded = true;

  document.addEventListener('nemt-get-fiber', function(e) {
    const idx = e.detail && e.detail.rowIndex;
    const rows = document.querySelectorAll('tr.ant-table-row');
    const row = rows[idx];
    let record = null;
    if (row) {
      try {
        const key = Object.keys(row).find(k =>
          k.startsWith('__reactFiber') ||
          k.startsWith('__reactInternalInstance')
        );
        if (key) {
          let fiber = row[key];
          let depth = 0;
          while (fiber && depth < 30) {
            const props = fiber.memoizedProps;
            if (props && props.record) { record = props.record; break; }
            fiber = fiber.return;
            depth++;
          }
        }
      } catch(err) {}
    }
    document.dispatchEvent(new CustomEvent('nemt-fiber-result', {
      detail: {
        rowIndex: idx,
        record: record ? JSON.parse(JSON.stringify(record)) : null
      }
    }));
  });

  document.addEventListener('nemt-toggle-check', function() {
    let btn = null;

    // Try 1: div[class*="toggleServiceArea-"] → click the div or its switch child
    const toggleDiv = document.querySelector('div[class*="toggleServiceArea-"]');
    if (toggleDiv) {
      btn = toggleDiv.querySelector('button.ant-switch, button[role="switch"]') || toggleDiv;
    }

    // Try 2: second button[role="switch"] on the page
    if (!btn) {
      const switches = document.querySelectorAll('button[role="switch"]');
      if (switches.length >= 2) btn = switches[1];
    }

    // Try 3: any ant-switch inside a toggleServiceArea ancestor
    if (!btn) {
      btn = document.querySelector('[class*="toggleServiceArea-"] button');
    }

    if (btn) {
      btn.click();
      document.dispatchEvent(new CustomEvent('nemt-toggle-clicked'));
    } else {
      document.dispatchEvent(new CustomEvent('nemt-toggle-not-found'));
    }
  });

  document.documentElement.dataset.nemtBridgeLoaded = '1';
  document.dispatchEvent(new CustomEvent('nemt-page-script-ready'));
  console.log('[NEMT BRIDGE] page_bridge.js loaded in MAIN world');
})();
