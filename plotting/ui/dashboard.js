// Retrieve configured parameters from window.SENATE_CONFIG
const {
  splitGeojson,
  outlinesGeojson,
  locs,
  pollsZCombined,
  pollsZOnly,
  legendColorsCombinedHtml,
  legendColorsPollsOnlyHtml,
  legendColorsHeatmapHtml,
  tooltips,
  stateNames,
  colorscale,
  contestedPatterns,
  abbrevLons,
  abbrevLats,
  abbrevTexts,
  flipLons,
  flipLats,
  flipColors,
  flipTexts,
  flipTooltips,
  numCategories,
  heatmapZ,
  heatmapColorscale,
  heatmapTooltips,
  heatmapZmin,
  heatmapZmax,
} = window.SENATE_CONFIG;

// Read persistent filter preference from sessionStorage
let isFilterActive = false;
try {
  isFilterActive = sessionStorage.getItem('senate_map_filter_only') === 'true';
} catch (e) {}

// Map traces definition
const mapTraceHalves = {
  type: 'choropleth',
  geojson: splitGeojson,
  locations: locs,
  featureidkey: 'id',
  z: isFilterActive ? pollsZOnly : pollsZCombined,
  colorscale: colorscale,
  zmin: -0.5,
  zmax: numCategories - 0.5,
  showscale: false,
  hoverinfo: 'text',
  hovertext: tooltips,
  marker: {
    line: { color: '#FFFFFF', width: 1.5 },
    opacity: 0.95
  }
};

const mapTraceOutlines = {
  type: 'choropleth',
  geojson: outlinesGeojson,
  locations: stateNames,
  featureidkey: 'id',
  z: new Array(stateNames.length).fill(0),
  colorscale: [[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
  showscale: false,
  hoverinfo: 'skip',
  marker: {
    line: { color: '#000000', width: 2.0 }
  }
};

const mapTraceText = {
  type: 'scattergeo',
  locationmode: 'USA-states',
  lon: abbrevLons,
  lat: abbrevLats,
  mode: 'text',
  text: abbrevTexts,
  textfont: {
    family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
    size: 10,
    color: '#FFFFFF'
  },
  showlegend: false,
  hoverinfo: 'skip'
};

// Style 2 Flip transfer badges: bold circular badge with ⇄ icon in incoming party color
const mapTraceFlips = {
  type: 'scattergeo',
  locationmode: 'USA-states',
  lon: flipLons,
  lat: flipLats,
  mode: 'markers+text',
  text: flipTexts,
  textposition: 'middle center',
  textfont: {
    family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
    size: 13,
    color: '#FFFFFF'
  },
  marker: {
    size: 22,
    color: flipColors,
    line: { color: '#FFFFFF', width: 2.0 },
    opacity: 1.0
  },
  showlegend: false,
  hoverinfo: 'text',
  hovertext: flipTooltips,
  name: 'Seat Flips'
};

const normalColorscale = colorscale;
const normalZmin = -0.5;
const normalZmax = numCategories - 0.5;

// Retrieve persistent zoom and pan state from sessionStorage
let savedGeoState = null;
try {
  const raw = sessionStorage.getItem('senate_map_geo_state');
  if (raw) savedGeoState = JSON.parse(raw);
} catch (e) {}

const mapLayout = {
  autosize: true,
  uirevision: 'senate_map_view',
  geo: {
    scope: 'usa',
    projection: {
      type: 'albers usa',
      scale: (savedGeoState && typeof savedGeoState.scale === 'number') ? savedGeoState.scale : 1.0
    },
    center: (savedGeoState && savedGeoState.center) ? savedGeoState.center : undefined,
    showsubunits: false,
    showland: false,
    showlakes: false,
    showocean: false,
    showrivers: false,
    showcountries: false,
    bgcolor: 'rgba(0,0,0,0)',
    domain: { x: [0, 1], y: [0, 1] }
  },
  margin: { l: 0, r: 0, t: 0, b: 0 },
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  hoverlabel: {
    bgcolor: '#0F172A',
    font: { size: 13, color: '#F8FAFC' },
    bordercolor: '#334155'
  },
  dragmode: 'pan',
  showlegend: false
};

// Apply diagonal hatch patterns and crisp white borders directly to Trace 0 paths
function applyContestedStyles() {
  const heatmapCb = document.getElementById('heatmap-toggle');
  if (heatmapCb && heatmapCb.checked) return;

  const choroplethTraces = document.querySelectorAll('#map-plot g.trace.choropleth, #map-plot g.choropleth');
  if (!choroplethTraces || choroplethTraces.length === 0) return;

  // Identify the 100-seat halves choropleth trace (Trace 0)
  let halvesTrace = null;
  for (const t of choroplethTraces) {
    const paths = t.querySelectorAll('path.choroplethlocation');
    if (paths.length === 100) {
      halvesTrace = t;
      break;
    }
  }
  if (!halvesTrace && choroplethTraces.length > 0) {
    halvesTrace = choroplethTraces[0];
  }
  if (!halvesTrace) return;

  // Clean any accidental classes on outline or other non-halves traces
  for (const t of choroplethTraces) {
    if (t !== halvesTrace) {
      const wrongPaths = t.querySelectorAll('path.contested-seat, path[class*="hatch-"]');
      wrongPaths.forEach(p => {
        p.classList.remove('contested-seat', 'hatch-dem', 'hatch-dem_lean', 'hatch-rep', 'hatch-rep_lean', 'hatch-ind', 'hatch-no_data', 'hatch-tie');
      });
    }
  }

  const halfPaths = halvesTrace.querySelectorAll('path.choroplethlocation');
  if (!halfPaths || halfPaths.length === 0) return;

  for (let idx = 0; idx < halfPaths.length; idx++) {
    const p = halfPaths[idx];
    let loc = null;
    const d = p.__data__;
    if (d) {
      loc = d.id || (d.properties && d.properties.id) || (d.properties && (d.properties.state + '_' + d.properties.side));
    }
    if (!loc && idx < locs.length) {
      loc = locs[idx];
    }
    const patternClass = contestedPatterns[loc];
    if (patternClass) {
      if (!p.classList.contains(patternClass)) {
        p.classList.add('contested-seat', patternClass);
      }
    }
  }
}

// Remove all pattern classes when heatmap gradient mode is active
function clearContestedStyles() {
  const choroplethTraces = document.querySelectorAll('#map-plot g.trace.choropleth, #map-plot g.choropleth');
  for (const t of choroplethTraces) {
    const paths = t.querySelectorAll('path.choroplethlocation');
    paths.forEach(p => {
      p.classList.remove('contested-seat', 'hatch-dem', 'hatch-dem_lean', 'hatch-rep', 'hatch-rep_lean', 'hatch-ind', 'hatch-no_data', 'hatch-tie');
    });
  }
}

// Save active zoom scale and center coordinates to sessionStorage
function saveCurrentGeoState(eventData) {
  const el = document.getElementById('map-plot');
  if (!el || !el._fullLayout || !el._fullLayout.geo) return;
  const g = el._fullLayout.geo;
  const state = {};

  if (g.projection && typeof g.projection.scale === 'number') {
    state.scale = g.projection.scale;
  }
  if (g.center && typeof g.center.lon === 'number' && typeof g.center.lat === 'number') {
    state.center = { lon: g.center.lon, lat: g.center.lat };
  }

  if (eventData) {
    if (typeof eventData['geo.projection.scale'] === 'number') {
      state.scale = eventData['geo.projection.scale'];
    }
    if (eventData['geo.center']) {
      state.center = eventData['geo.center'];
    }
    if (typeof eventData['geo.center.lon'] === 'number' && typeof eventData['geo.center.lat'] === 'number') {
      state.center = { lon: eventData['geo.center.lon'], lat: eventData['geo.center.lat'] };
    }
  }

  if (state.scale !== undefined || state.center !== undefined) {
    try {
      sessionStorage.setItem('senate_map_geo_state', JSON.stringify(state));
    } catch (e) {}
  }
}

// Initial render with interactive pan and zoom
// Trace indices: 0=halves, 1=outlines, 2=abbrevText, 3=flips
Plotly.newPlot('map-plot', [mapTraceHalves, mapTraceOutlines, mapTraceText, mapTraceFlips], mapLayout, {
  responsive: true,
  displayModeBar: false,
  scrollZoom: true
}).then(() => {
  if (savedGeoState && (savedGeoState.scale !== 1.0 || savedGeoState.center)) {
    const update = {};
    if (typeof savedGeoState.scale === 'number') {
      update['geo.projection.scale'] = savedGeoState.scale;
    }
    if (savedGeoState.center) {
      update['geo.center'] = savedGeoState.center;
    }
    Plotly.relayout('map-plot', update).then(() => {
      applyContestedStyles();
    }).catch(() => {
      applyContestedStyles();
    });
  } else {
    applyContestedStyles();
  }
});

// Reliable autosize relayout without fragile mutex locks
function resizeMap() {
  const el = document.getElementById('map-plot');
  if (!el || !el.data) return;
  try {
    Plotly.relayout(el, { autosize: true }).then(() => {
      applyContestedStyles();
    }).catch(() => {
      applyContestedStyles();
    });
  } catch (err) {
    applyContestedStyles();
  }
}

let resizeTimer = null;
function debouncedResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(resizeMap, 80);
}

window.addEventListener('resize', debouncedResize);

// Hook Plotly redraw events safely to re-apply pattern classes and track view changes
const mapDiv = document.getElementById('map-plot');
if (mapDiv && mapDiv.on) {
  mapDiv.on('plotly_afterplot', () => {
    applyContestedStyles();
  });
  mapDiv.on('plotly_relayout', (eventData) => {
    applyContestedStyles();
    saveCurrentGeoState(eventData);
  });
}

// ResizeObserver on the container to detect flexbox layout updates
const ro = new ResizeObserver(() => {
  debouncedResize();
});
const mapPlot = document.getElementById('map-plot');
if (mapPlot) {
  ro.observe(mapPlot);
}

// Wire in-map client-side filter toggle: instant restyle, zero map regeneration, zoom 100% frozen
const filterCheckbox = document.getElementById('client-filter-toggle');
const heatmapCheckbox = document.getElementById('heatmap-toggle');
const legendColorsContainer = document.getElementById('legend-colors-container');

if (filterCheckbox) {
  if (isFilterActive) {
    filterCheckbox.checked = true;
    if (legendColorsContainer) {
      legendColorsContainer.innerHTML = legendColorsPollsOnlyHtml;
    }
  }

  filterCheckbox.addEventListener('change', (e) => {
    const checked = e.target.checked;
    // Heatmap mode takes priority over this toggle — ignore if heatmap is active
    if (heatmapCheckbox && heatmapCheckbox.checked) return;
    const targetZ = checked ? pollsZOnly : pollsZCombined;

    // Instant update via Plotly.restyle: 0ms latency, zero map regeneration, zoom 100% frozen
    Plotly.restyle('map-plot', { z: [targetZ] }, [0]).then(() => {
      applyContestedStyles();
    });

    if (legendColorsContainer) {
      legendColorsContainer.innerHTML = checked ? legendColorsPollsOnlyHtml : legendColorsCombinedHtml;
    }

    try {
      sessionStorage.setItem('senate_map_filter_only', checked ? 'true' : 'false');
    } catch (err) {}
  });
}

// Wire voter-weight heatmap toggle: native restyle on Trace 0, zero DOM recreation, zoom 100% frozen
if (heatmapCheckbox) {
  heatmapCheckbox.addEventListener('change', (e) => {
    const isHeatmap = e.target.checked;

    if (isHeatmap) {
      clearContestedStyles();
      if (filterCheckbox) filterCheckbox.disabled = true;

      Plotly.restyle('map-plot', {
        z: [heatmapZ],
        colorscale: [heatmapColorscale],
        zmin: heatmapZmin,
        zmax: heatmapZmax,
        hovertext: [heatmapTooltips]
      }, [0]).then(() => {
        clearContestedStyles();
      });

      if (legendColorsContainer) {
        legendColorsContainer.innerHTML = legendColorsHeatmapHtml;
      }
    } else {
      if (filterCheckbox) filterCheckbox.disabled = false;

      const targetZ = (filterCheckbox && filterCheckbox.checked) ? pollsZOnly : pollsZCombined;

      Plotly.restyle('map-plot', {
        z: [targetZ],
        colorscale: [normalColorscale],
        zmin: normalZmin,
        zmax: normalZmax,
        hovertext: [tooltips]
      }, [0]).then(() => {
        applyContestedStyles();
      });

      if (legendColorsContainer) {
        legendColorsContainer.innerHTML = (filterCheckbox && filterCheckbox.checked)
          ? legendColorsPollsOnlyHtml
          : legendColorsCombinedHtml;
      }
    }
  });
}

// Wire reset zoom button
const resetZoomBtn = document.getElementById('reset-zoom-btn');
if (resetZoomBtn) {
  resetZoomBtn.addEventListener('click', () => {
    try {
      sessionStorage.removeItem('senate_map_geo_state');
    } catch (e) {}

    Plotly.relayout('map-plot', {
      'geo.projection.scale': 1.0,
      'geo.center': null
    }).then(() => {
      applyContestedStyles();
    });
  });
}
