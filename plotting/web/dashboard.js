/**
 * 2026 US Senate Interactive Election Visualization (Web Native)
 *
 * Fetches preprocessed data from ./data/senate_data.json and GeoJSON collections,
 * initializing Plotly.js choropleth halves, boundary outlines, postal abbreviations,
 * and circular transfer badges with client-side interactive toggles.
 */

(async function initDashboard() {
  try {
    // Concurrent fetch of all required static data assets
    const [senateData, splitGeojson, outlinesGeojson] = await Promise.all([
      fetch('./data/senate_data.json').then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} fetching senate_data.json`);
        return r.json();
      }),
      fetch('./data/_us_states_split.geojson').then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} fetching split GeoJSON`);
        return r.json();
      }),
      fetch('./data/_us_states_outlines.geojson').then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} fetching outlines GeoJSON`);
        return r.json();
      }),
    ]);

    const {
      summary,
      badges,
      locs,
      pollsZCombined,
      pollsZOnly,
      tooltips,
      stateNames,
      colorscale,
      numCategories,
      contestedPatterns,
      abbrevLons,
      abbrevLats,
      abbrevTexts,
      heatmapZ,
      heatmapColorscale,
      heatmapTooltips,
      heatmapStateZ,
      heatmapStateTooltips,
      heatmapZmin,
      heatmapZmax,
      legendColorsCombinedHtml,
      legendColorsPollsOnlyHtml,
      legendColorsHeatmapHtml,
    } = senateData;

    // Render Balance of Power Panel HTML dynamically
    function renderBalancePanel(s) {

      const barTally = document.getElementById('bar-header-tally');
      if (barTally) {
        barTally.textContent = `DEM crosses 50-Seat Mark (${s.projected_dem_total} DEM vs. ${s.projected_rep_total} REP)`;
      }

      const repFlipBar = s.rep_flips > 0
        ? `<div class="bar-seg seg-rep-flips" style="width: ${s.rep_flips}%;" title="${s.rep_flips} Republican Flip from DEM (${s.rep_flip_states})">+${s.rep_flips}★</div>`
        : '';

      const barTrack = document.getElementById('balance-bar-track');
      if (barTrack) {
        barTrack.innerHTML = `
          <div class="bar-seg seg-dem-safe" style="width: ${s.safe_dem_ind}%;" title="${s.safe_dem_ind} Safe Democratic & Independent Seats">${s.safe_dem_ind} Safe</div>
          <div class="bar-seg seg-dem-holds" style="width: ${s.dem_holds}%;" title="${s.dem_holds} Democratic Poll Holds">${s.dem_holds} Holds</div>
          <div class="bar-seg seg-dem-flips" style="width: ${s.dem_flips}%;" title="${s.dem_flips} Democratic Flips from GOP (${s.dem_flip_states})">+${s.dem_flips}★</div>
          <div class="bar-seg seg-unpolled" style="width: ${s.unpolled}%;" title="${s.unpolled} Seats with No General Election Polls (${s.unpolled_dem} DEM, ${s.unpolled_rep} REP)">${s.unpolled}</div>
          ${repFlipBar}
          <div class="bar-seg seg-rep-holds" style="width: ${s.rep_holds}%;" title="${s.rep_holds} Republican Poll Holds">${s.rep_holds} Holds</div>
          <div class="bar-seg seg-rep-safe" style="width: ${s.safe_rep}%;" title="${s.safe_rep} Safe Republican Seats">${s.safe_rep} Safe</div>
        `;
      }

      const sublegend = document.getElementById('bar-sublegend');
      if (sublegend) {
        sublegend.innerHTML = `
          <span>🔵 <b>${s.projected_dem_total} DEM Coalition</b> (${s.safe_dem_ind} Safe + ${s.dem_holds} Holds + ${s.dem_flips} Flips + ${s.unpolled_dem} Unpolled)</span>
          <span>🔴 <b>${s.projected_rep_total} Republican Party</b> (${s.safe_rep} Safe + ${s.rep_holds} Holds + ${s.rep_flips} Flips + ${s.unpolled_rep} Unpolled)</span>
        `;
      }

      const repFlipLegend = s.rep_flips > 0
        ? `<div class="legend-item"><span class="legend-swatch" style="background:#F87171;"></span> <b>+${s.rep_flips}</b> REP Flip (Gain)</div>`
        : '';

      const legendGrid = document.getElementById('bar-legend-grid');
      if (legendGrid) {
        legendGrid.innerHTML = `
          <div class="legend-item"><span class="legend-swatch" style="background:#1E40AF;"></span> <b>${s.safe_dem_ind}</b> Safe DEM & IND</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <b>${s.dem_holds}</b> DEM Holds</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#0284C7; border: 1px solid #38BDF8;"></span> <b>+${s.dem_flips}</b> DEM Flips (Gain)</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#64748B;"></span> <b>${s.unpolled}</b> Unpolled Seats</div>
          ${repFlipLegend}
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <b>${s.rep_holds}</b> REP Holds</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#991B1B;"></span> <b>${s.safe_rep}</b> Safe REP</div>
        `;
      }
    }

    renderBalancePanel(summary);

    // Initial legend colors container
    const legendColorsContainer = document.getElementById('legend-colors-container');
    if (legendColorsContainer) {
      legendColorsContainer.innerHTML = legendColorsCombinedHtml;
    }

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
        opacity: 0.95,
      },
    };

    const outlineTransparentColorscale = [[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']];
    const outlineZeros = new Array(stateNames.length).fill(0);

    const mapTraceOutlines = {
      type: 'choropleth',
      geojson: outlinesGeojson,
      locations: stateNames,
      featureidkey: 'id',
      z: outlineZeros,
      colorscale: outlineTransparentColorscale,
      showscale: false,
      hoverinfo: 'skip',
      marker: {
        line: { color: '#000000', width: 2.0 },
      },
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
        color: '#FFFFFF',
      },
      showlegend: false,
      hoverinfo: 'skip',
    };

    const activeBadges = badges['none'] || badges;
    const mapTraceFlips = {
      type: 'scattergeo',
      locationmode: 'USA-states',
      lon: activeBadges.lons,
      lat: activeBadges.lats,
      mode: 'markers+text',
      text: activeBadges.texts,
      textposition: 'middle center',
      textfont: {
        family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
        size: 13,
        color: '#FFFFFF',
      },
      marker: {
        size: 22,
        color: activeBadges.colors,
        line: { color: '#FFFFFF', width: 2.0 },
        opacity: 1.0,
      },
      showlegend: false,
      hoverinfo: 'text',
      hovertext: activeBadges.tooltips,
      name: 'Seat Flips',
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
          scale: (savedGeoState && typeof savedGeoState.scale === 'number') ? savedGeoState.scale : 1.0,
        },
        center: (savedGeoState && savedGeoState.center) ? savedGeoState.center : undefined,
        showsubunits: false,
        showland: false,
        showlakes: false,
        showocean: false,
        showrivers: false,
        showcountries: false,
        bgcolor: 'rgba(0,0,0,0)',
        domain: { x: [0, 1], y: [0, 1] },
      },
      margin: { l: 0, r: 0, t: 0, b: 0 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      hoverlabel: {
        bgcolor: '#0F172A',
        font: { size: 13, color: '#F8FAFC' },
        bordercolor: '#334155',
      },
      dragmode: 'pan',
      showlegend: false,
    };

    // Apply diagonal hatch patterns and borders to Trace 0 paths
    function applyContestedStyles() {
      const heatmapCb = document.getElementById('heatmap-toggle');
      if (heatmapCb && heatmapCb.checked) return;

      const choroplethTraces = document.querySelectorAll('#map-plot g.trace.choropleth, #map-plot g.choropleth');
      if (!choroplethTraces || choroplethTraces.length === 0) return;

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

      for (const t of choroplethTraces) {
        if (t !== halvesTrace) {
          const wrongPaths = t.querySelectorAll('path.contested-seat, path[class*="hatch-"]');
          wrongPaths.forEach((p) => {
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

    function clearContestedStyles() {
      const choroplethTraces = document.querySelectorAll('#map-plot g.trace.choropleth, #map-plot g.choropleth');
      for (const t of choroplethTraces) {
        const paths = t.querySelectorAll('path.choroplethlocation');
        paths.forEach((p) => {
          p.classList.remove('contested-seat', 'hatch-dem', 'hatch-dem_lean', 'hatch-rep', 'hatch-rep_lean', 'hatch-ind', 'hatch-no_data', 'hatch-tie');
        });
      }
    }

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

    // Initial render
    Plotly.newPlot('map-plot', [mapTraceHalves, mapTraceOutlines, mapTraceText, mapTraceFlips], mapLayout, {
      responsive: true,
      displayModeBar: false,
      scrollZoom: true,
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

    const ro = new ResizeObserver(() => {
      debouncedResize();
    });
    const mapPlot = document.getElementById('map-plot');
    if (mapPlot) {
      ro.observe(mapPlot);
    }

    // Wire in-map client-side filter toggle
    const filterCheckbox = document.getElementById('client-filter-toggle');
    const heatmapCheckbox = document.getElementById('heatmap-toggle');
    const legendBar = document.getElementById('map-legend-bar');

    // Always reset heatmap toggle on page load to prevent stale browser form restore
    if (heatmapCheckbox) {
      heatmapCheckbox.checked = false;
    }
    if (legendBar) {
      legendBar.classList.remove('heatmap-mode');
    }

    if (filterCheckbox) {
      if (isFilterActive) {
        filterCheckbox.checked = true;
        if (legendColorsContainer) {
          legendColorsContainer.innerHTML = legendColorsPollsOnlyHtml;
        }
      }

      filterCheckbox.addEventListener('change', (e) => {
        const checked = e.target.checked;
        if (heatmapCheckbox && heatmapCheckbox.checked) return;
        const targetZ = checked ? pollsZOnly : pollsZCombined;

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

    // Wire voter-weight heatmap toggle
    if (heatmapCheckbox) {
      heatmapCheckbox.addEventListener('change', (e) => {
        const isHeatmap = e.target.checked;

        if (isHeatmap) {
          if (legendBar) legendBar.classList.add('heatmap-mode');
          clearContestedStyles();
          if (filterCheckbox) filterCheckbox.disabled = true;

          // 1. Hide split-halves trace 0 to eliminate any middle seam
          // 2. Color whole-state outlines trace 1 with continuous heatmap data
          // 3. Mute flip markers trace 3
          Plotly.restyle('map-plot', { visible: false }, [0])
            .then(() => {
              return Plotly.restyle('map-plot', {
                z: [heatmapStateZ],
                colorscale: [heatmapColorscale],
                zmin: heatmapZmin,
                zmax: heatmapZmax,
                hovertext: [heatmapStateTooltips],
                hoverinfo: 'text',
                'marker.line.color': '#000000',
                'marker.line.width': 1.5,
              }, [1]);
            })
            .then(() => {
              return Plotly.restyle('map-plot', { visible: false }, [3]);
            });

          if (legendColorsContainer) {
            legendColorsContainer.innerHTML = legendColorsHeatmapHtml;
          }
        } else {
          if (legendBar) legendBar.classList.remove('heatmap-mode');
          if (filterCheckbox) filterCheckbox.disabled = false;
          const targetZ = (filterCheckbox && filterCheckbox.checked) ? pollsZOnly : pollsZCombined;

          // 1. Reset whole-state trace 1 back to transparent outlines
          // 2. Restore split-halves trace 0 with categorical data and white inner seat borders
          // 3. Restore flip markers trace 3
          Plotly.restyle('map-plot', {
            z: [outlineZeros],
            colorscale: [outlineTransparentColorscale],
            hoverinfo: 'skip',
            'marker.line.color': '#000000',
            'marker.line.width': 2.0,
          }, [1])
            .then(() => {
              return Plotly.restyle('map-plot', {
                z: [targetZ],
                colorscale: [normalColorscale],
                zmin: normalZmin,
                zmax: normalZmax,
                hovertext: [tooltips],
                visible: true,
                'marker.line.width': 1.5,
                'marker.line.color': '#FFFFFF',
              }, [0]);
            })
            .then(() => {
              return Plotly.restyle('map-plot', { visible: true }, [3]);
            })
            .then(() => {
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
          'geo.center': null,
        }).then(() => {
          applyContestedStyles();
        });
      });
    }
  } catch (err) {
    console.error('Error initializing Senate dashboard:', err);
  }
})();
