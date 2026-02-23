/**
 * SCODA Desktop — Generic Viewer
 * Manifest-driven frontend for browsing SCODA data packages
 */

// Defaults
const BOOLEAN_TRUE_LABEL = 'True';
const BOOLEAN_FALSE_LABEL = 'False';

// State
let selectedLeafId = null;
let detailModal = null;
let currentItems = [];  // Store current leaf items for filtering
let showOnlyValid = true;  // Filter state

// Manifest state
let manifest = null;
let currentView = null;
let currentTreeViewKey = null;  // Which manifest view key is the active tree view
let tableViewData = [];
let tableViewSort = null;
let tableViewSearchTerm = '';

// Shared query cache — fetch once, reuse across search index + tab views
let queryCache = {};

// Global search state
let searchIndex = null;
let searchIndexLoading = false;
let searchResults = [];
let searchHighlightIndex = -1;
let searchExpandedCategories = {};
let searchDebounceTimer = null;
let searchCategories = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    detailModal = new bootstrap.Modal(document.getElementById('detailModal'));
    await loadManifest();

    // Determine initial view from manifest
    if (manifest && manifest.views) {
        const viewKeys = Object.keys(manifest.views).filter(k => manifest.views[k].type !== 'detail');
        if (manifest.default_view && manifest.views[manifest.default_view]) {
            currentView = manifest.default_view;
        } else if (viewKeys.length > 0) {
            currentView = viewKeys[0];
        }
        if (currentView) {
            buildViewTabs();
            switchToView(currentView);
        }
    }

    // Global search — preload all data into shared cache
    initGlobalSearch();
    preloadSearchIndex();
});

/**
 * Load UI manifest from API (graceful degradation if unavailable)
 */
async function loadManifest() {
    try {
        const response = await fetch('/api/manifest');
        if (!response.ok) return;
        const data = await response.json();
        manifest = data.manifest;

        // Normalize legacy view types to unified hierarchy
        if (manifest && manifest.views) {
            for (const key of Object.keys(manifest.views)) {
                normalizeViewDef(manifest.views[key]);
            }
        }

        buildViewTabs();

        // Show package name in navbar
        if (data.package && data.package.name) {
            const el = document.getElementById('navbar-pkg-name');
            if (el) el.textContent = `${data.package.name} v${data.package.version}`;
        }
    } catch (error) {
        // Graceful degradation: manifest unavailable, use existing UI
    }
}

/**
 * Fetch a named query with caching. Returns cached rows if available.
 */
async function fetchQuery(queryName) {
    if (queryCache[queryName]) return queryCache[queryName];
    const url = `/api/queries/${queryName}/execute`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Query failed: ${queryName}`);
    const data = await response.json();
    queryCache[queryName] = data.rows || [];
    return queryCache[queryName];
}

/**
 * Normalize legacy view definitions to unified hierarchy type.
 * type:"tree" + tree_options → type:"hierarchy", display:"tree", hierarchy_options + tree_display
 * type:"chart" + chart_options → type:"hierarchy", display:"nested_table", hierarchy_options + nested_table_display
 */
function normalizeViewDef(viewDef) {
    if (viewDef.type === 'tree' && viewDef.tree_options) {
        const to = viewDef.tree_options;
        viewDef.type = 'hierarchy';
        viewDef.display = 'tree';
        viewDef.hierarchy_options = {
            id_key: to.id_key || 'id',
            parent_key: to.parent_key || 'parent_id',
            label_key: to.label_key || 'name',
            rank_key: to.rank_key || 'rank',
            sort_by: 'label',
            order_key: to.id_key || 'id',
            skip_ranks: []
        };
        viewDef.tree_display = {
            leaf_rank: to.leaf_rank,
            count_key: to.count_key,
            on_node_info: to.on_node_info,
            item_query: to.item_query,
            item_param: to.item_param,
            item_columns: to.item_columns,
            on_item_click: to.on_item_click,
            item_valid_filter: to.item_valid_filter
        };
        delete viewDef.tree_options;
    } else if (viewDef.type === 'chart' && viewDef.chart_options) {
        const co = viewDef.chart_options;
        viewDef.type = 'hierarchy';
        viewDef.display = 'nested_table';
        viewDef.hierarchy_options = {
            id_key: co.id_key || 'id',
            parent_key: co.parent_key || 'parent_id',
            label_key: co.label_key || 'name',
            rank_key: co.rank_key || 'rank',
            sort_by: 'order_key',
            order_key: co.order_key || 'id',
            skip_ranks: co.skip_ranks || []
        };
        viewDef.nested_table_display = {
            color_key: co.color_key,
            rank_columns: co.rank_columns,
            value_column: co.value_column,
            cell_click: co.cell_click
        };
        delete viewDef.chart_options;
    }
    return viewDef;
}

/**
 * Build view tabs from manifest
 */
function buildViewTabs() {
    if (!manifest || !manifest.views) return;

    const tabsContainer = document.getElementById('view-tabs');
    let html = '';

    for (const [key, view] of Object.entries(manifest.views)) {
        // Skip detail type views (they're not top-level tabs)
        if (view.type === 'detail') continue;

        const isActive = key === currentView;
        const icon = view.icon || 'bi-square';
        html += `<button class="view-tab ${isActive ? 'active' : ''}"
                         data-view="${key}" onclick="switchToView('${key}')">
                    <i class="bi ${icon}"></i> ${view.title}
                 </button>`;
    }

    tabsContainer.innerHTML = html;
}

/**
 * Switch between views
 */
function switchToView(viewKey) {
    if (!manifest || !manifest.views[viewKey]) return;

    currentView = viewKey;
    const view = manifest.views[viewKey];

    // Update tab active state
    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === viewKey);
    });

    // Show/hide view containers
    const treeContainer = document.getElementById('view-tree');
    const tableContainer = document.getElementById('view-table');
    const chartContainer = document.getElementById('view-chart');

    treeContainer.style.display = 'none';
    tableContainer.style.display = 'none';
    chartContainer.style.display = 'none';

    if (view.type === 'hierarchy') {
        if (view.display === 'tree') {
            currentTreeViewKey = viewKey;
            treeContainer.style.display = '';
            loadTree();
        } else if (view.display === 'nested_table') {
            chartContainer.style.display = '';
            renderNestedTableView(viewKey);
        }
    } else if (view.type === 'table') {
        tableContainer.style.display = '';
        tableViewSort = view.default_sort || null;
        tableViewSearchTerm = '';
        renderTableView(viewKey);
    }
}

/**
 * Render a table view using manifest definition and query execution
 */
async function renderTableView(viewKey) {
    const view = manifest.views[viewKey];
    if (!view || view.type !== 'table') return;

    const header = document.getElementById('table-view-header');
    const toolbar = document.getElementById('table-view-toolbar');
    const body = document.getElementById('table-view-body');

    // Header
    header.innerHTML = `<h5><i class="bi ${view.icon || 'bi-table'}"></i> ${view.title}</h5>
                        <p class="text-muted mb-0">${view.description || ''}</p>`;

    // Toolbar (search)
    if (view.searchable) {
        toolbar.innerHTML = `<div class="table-view-search">
            <i class="bi bi-search"></i>
            <input type="text" class="form-control form-control-sm"
                   placeholder="Search..." id="table-search-input"
                   oninput="onTableSearch(this.value)" value="${tableViewSearchTerm}">
        </div>`;
    } else {
        toolbar.innerHTML = '';
    }

    // Load data (from shared cache or fetch)
    body.innerHTML = '<div class="loading">Loading...</div>';

    try {
        tableViewData = await fetchQuery(view.source_query);
        renderTableViewRows(viewKey);
    } catch (error) {
        body.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

/**
 * Render table rows with current sort and search applied
 */
function renderTableViewRows(viewKey) {
    const view = manifest.views[viewKey];
    if (!view || !view.columns) return;

    const body = document.getElementById('table-view-body');
    let rows = [...tableViewData];

    // Apply search
    if (tableViewSearchTerm) {
        const term = tableViewSearchTerm.toLowerCase();
        const searchableCols = view.columns.filter(c => c.searchable).map(c => c.key);
        rows = rows.filter(row =>
            searchableCols.some(key => {
                const val = row[key];
                return val && String(val).toLowerCase().includes(term);
            })
        );
    }

    // Apply sort
    if (tableViewSort) {
        const { key, direction } = tableViewSort;
        rows.sort((a, b) => {
            let va = a[key], vb = b[key];
            if (va == null) va = '';
            if (vb == null) vb = '';
            if (typeof va === 'number' && typeof vb === 'number') {
                return direction === 'asc' ? va - vb : vb - va;
            }
            va = String(va).toLowerCase();
            vb = String(vb).toLowerCase();
            if (va < vb) return direction === 'asc' ? -1 : 1;
            if (va > vb) return direction === 'asc' ? 1 : -1;
            return 0;
        });
    }

    // Build table
    let html = `<div class="table-view-stats text-muted mb-2">${rows.length} of ${tableViewData.length} records</div>`;
    html += '<table class="manifest-table"><thead><tr>';

    view.columns.forEach(col => {
        const sortIcon = getSortIcon(col.key);
        const sortable = col.sortable ? `onclick="onTableSort('${viewKey}', '${col.key}')"` : '';
        const sortableClass = col.sortable ? 'sortable' : '';
        html += `<th class="${sortableClass}" ${sortable}>${col.label} ${sortIcon}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Manifest-driven click handler
    const rowClick = view.on_row_click;
    const getClick = rowClick
        ? (row) => `onclick="openDetail('${rowClick.detail_view}', ${row[rowClick.id_key]})"`
        : null;

    if (rows.length === 0) {
        html += `<tr><td colspan="${view.columns.length}" class="text-center text-muted py-4">No matching records</td></tr>`;
    } else {
        rows.forEach(row => {
            const clickAttr = getClick ? getClick(row) : '';
            html += `<tr ${clickAttr}>`;
            view.columns.forEach(col => {
                let val = row[col.key];
                if (col.type === 'color') {
                    const color = val || '';
                    val = color ? `<span class="color-chip" style="background-color:${color}" title="${color}"></span> ${color}` : '';
                } else if (col.type === 'boolean') {
                    val = val ? (col.true_label || BOOLEAN_TRUE_LABEL) : (col.false_label || BOOLEAN_FALSE_LABEL);
                } else if (val == null) {
                    val = '';
                }
                const italic = col.italic ? `<i>${val}</i>` : val;
                html += `<td>${italic}</td>`;
            });
            html += '</tr>';
        });
    }

    html += '</tbody></table>';
    body.innerHTML = html;
}

/**
 * Get sort indicator icon for a column
 */
function getSortIcon(key) {
    if (!tableViewSort || tableViewSort.key !== key) return '';
    return tableViewSort.direction === 'asc'
        ? '<i class="bi bi-caret-up-fill"></i>'
        : '<i class="bi bi-caret-down-fill"></i>';
}

/**
 * Handle table column sort click
 */
function onTableSort(viewKey, key) {
    if (tableViewSort && tableViewSort.key === key) {
        tableViewSort.direction = tableViewSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        tableViewSort = { key, direction: 'asc' };
    }
    renderTableViewRows(viewKey);
}

/**
 * Handle table search input
 */
function onTableSearch(value) {
    tableViewSearchTerm = value;
    renderTableViewRows(currentView);
}

/**
 * Render ICS Chronostratigraphic Chart as a hierarchical colored table
 */
async function renderNestedTableView(viewKey) {
    const view = manifest.views[viewKey];
    if (!view) return;

    const hOpts = view.hierarchy_options || {};
    const ntOpts = view.nested_table_display || {};
    const opts = { ...hOpts, ...ntOpts };

    const header = document.getElementById('chart-view-header');
    const body = document.getElementById('chart-view-body');

    header.innerHTML = `<h5><i class="bi ${view.icon || 'bi-clock-history'}"></i> ${view.title}</h5>
                        <p class="text-muted mb-0">${view.description || ''}</p>`;

    body.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const rows = await fetchQuery(view.source_query);

        // Build rank→column mapping from manifest
        const rankColumns = opts.rank_columns || [
            {rank: 'Eon'}, {rank: 'Era'}, {rank: 'Period'},
            {rank: 'Sub-Period'}, {rank: 'Epoch'}, {rank: 'Age'}
        ];
        const rankColMap = {};
        rankColumns.forEach((rc, i) => { rankColMap[rc.rank] = i; });
        const colCount = rankColumns.length + 1; // +1 for value column

        // Build tree from flat data
        const tree = buildHierarchy(rows, hOpts);
        // Compute leaf counts for rowspan
        tree.forEach(node => computeLeafCount(node));
        // Collect leaf rows (each row = root→leaf path)
        const leafRows = [];
        tree.forEach(node => collectLeafRows(node, [], leafRows, 0, rankColMap, opts));

        // Render HTML table
        body.innerHTML = renderChartHTML(leafRows, opts);
    } catch (error) {
        body.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

/**
 * Build tree from flat rows (unified hierarchy builder).
 * sort_by: "label" (alphabetical) or "order_key" (numerical).
 * skip_ranks: ranks to skip (children promoted to parent level).
 */
function buildHierarchy(rows, opts) {
    opts = opts || {};
    const idKey = opts.id_key || 'id';
    const parentKey = opts.parent_key || 'parent_id';
    const labelKey = opts.label_key || 'name';
    const rankKey = opts.rank_key || 'rank';
    const sortBy = opts.sort_by || 'label';
    const orderKey = opts.order_key || 'id';
    const skipRanks = opts.skip_ranks || [];

    const byId = {};
    rows.forEach(r => { byId[r[idKey]] = { ...r, children: [] }; });

    const roots = [];
    rows.forEach(r => {
        const node = byId[r[idKey]];
        if (r[parentKey] && byId[r[parentKey]]) {
            const parent = byId[r[parentKey]];
            if (skipRanks.includes(parent[rankKey])) {
                roots.push(node);
            } else {
                parent.children.push(node);
            }
        } else if (!r[parentKey]) {
            if (skipRanks.includes(r[rankKey])) {
                // Don't add skipped rank itself; its children will be promoted
            } else {
                roots.push(node);
            }
        }
    });

    // Sort based on sort_by option
    function sortChildren(node) {
        if (sortBy === 'order_key') {
            node.children.sort((a, b) => (a[orderKey] || 0) - (b[orderKey] || 0));
        } else {
            node.children.sort((a, b) => (a[labelKey] || '').localeCompare(b[labelKey] || ''));
        }
        node.children.forEach(sortChildren);
    }
    if (sortBy === 'order_key') {
        roots.sort((a, b) => (a[orderKey] || 0) - (b[orderKey] || 0));
    } else {
        roots.sort((a, b) => (a[labelKey] || '').localeCompare(b[labelKey] || ''));
    }
    roots.forEach(sortChildren);

    return roots;
}

/**
 * Compute leaf count for each node (= rowspan).
 * A leaf node (no children) has leafCount = 1.
 */
function computeLeafCount(node) {
    if (node.children.length === 0) {
        node.leafCount = 1;
        return 1;
    }
    let count = 0;
    node.children.forEach(c => { count += computeLeafCount(c); });
    node.leafCount = count;
    return count;
}

/**
 * Check if a node has a direct child at the next rank column (for colspan calculation).
 * e.g., Period (col 2) checking if any child is Sub-Period (col 3).
 */
function hasDirectChildRank(node, parentCol, rankColMap, rankKey) {
    return node.children.some(c => rankColMap[c[rankKey]] === parentCol + 1);
}

/**
 * Collect leaf rows via DFS. Each leaf produces one table row.
 * path = array of { node, col, colspan, rowspan } for ancestors that start at this leaf's row.
 * parentEndCol = the first column after the parent's span (used to detect gaps like Pridoli)
 * rankColMap = rank→column index mapping from nested_table_display
 */
function collectLeafRows(node, ancestorPath, leafRows, parentEndCol, rankColMap, opts) {
    opts = opts || {};
    const rankKey = opts.rank_key || 'rank';
    const maxCol = Object.keys(rankColMap).length - 1; // last rank column index

    let col = rankColMap[node[rankKey]] !== undefined ? rankColMap[node[rankKey]] : maxCol;

    // If node has children but no direct child at col+1, extend colspan to bridge the gap
    let colspan = 1;
    if (node.children.length > 0 && !hasDirectChildRank(node, col, rankColMap, rankKey)) {
        const childCols = node.children.map(c => rankColMap[c[rankKey]]).filter(c => c !== undefined);
        if (childCols.length > 0) {
            const minChildCol = Math.min(...childCols);
            if (minChildCol > col + 1) {
                colspan = minChildCol - col;
            }
        }
    }

    // Adjust for parent-child column gap (e.g., Pridoli: Age directly under Period)
    if (parentEndCol !== undefined && col > parentEndCol) {
        const originalEndCol = col + colspan - 1;
        col = parentEndCol;
        colspan = originalEndCol - col + 1;
    }

    const entry = { node, col, colspan, rowspan: node.leafCount };
    const myEndCol = col + colspan;

    if (node.children.length === 0) {
        // Leaf: extend colspan to fill remaining columns up to last rank column
        const endCol = col + colspan - 1;
        if (endCol < maxCol) {
            colspan = maxCol - col + 1; // extend to last rank col inclusive
            entry.colspan = colspan;
        }

        // Build the row: ancestor cells + this cell
        const row = [...ancestorPath, entry];
        leafRows.push(row);
    } else {
        // Non-leaf: first child inherits this node in its path, rest don't
        node.children.forEach((child, i) => {
            if (i === 0) {
                collectLeafRows(child, [...ancestorPath, entry], leafRows, myEndCol, rankColMap, opts);
            } else {
                collectLeafRows(child, [], leafRows, myEndCol, rankColMap, opts);
            }
        });
    }
}

/**
 * Determine if a hex color is light (for text contrast)
 */
function isLightColor(hex) {
    if (!hex) return true;
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    // Luminance formula
    const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return lum > 0.5;
}

/**
 * Render the ICS chart as an HTML table (manifest-driven)
 */
function renderChartHTML(leafRows, opts) {
    opts = opts || {};
    const rankColumns = opts.rank_columns || [
        {rank: 'Eon', label: 'Eon'}, {rank: 'Era', label: 'Era'},
        {rank: 'Period', label: 'System / Period'}, {rank: 'Sub-Period', label: 'Sub-Period'},
        {rank: 'Epoch', label: 'Series / Epoch'}, {rank: 'Age', label: 'Stage / Age'}
    ];
    const valueCol = opts.value_column || {key: 'start_mya', label: 'Age (Ma)'};
    const cellClick = opts.cell_click || {id_key: 'id'};
    const labelKey = opts.label_key || 'name';
    const colorKey = opts.color_key || 'color';
    const idKey = opts.id_key || 'id';

    const headers = rankColumns.map(rc => rc.label).concat(valueCol.label);

    let html = '<table class="ics-chart"><thead><tr>';
    headers.forEach(h => { html += `<th>${h}</th>`; });
    html += '</tr></thead><tbody>';

    leafRows.forEach(row => {
        html += '<tr>';
        // Render ancestor + leaf cells
        row.forEach(entry => {
            const n = entry.node;
            const bgColor = n[colorKey] || '#f8f9fa';
            const textColor = isLightColor(bgColor) ? '#222' : '#fff';
            const rs = entry.rowspan > 1 ? ` rowspan="${entry.rowspan}"` : '';
            const cs = entry.colspan > 1 ? ` colspan="${entry.colspan}"` : '';
            const vk = valueCol.key;
            const title = n[vk] != null ? `${n[labelKey]} (${n[vk]}–${n.end_mya || 0} Ma)` : n[labelKey];
            const clickAttr = cellClick.detail_view
                ? `onclick="openDetail('${cellClick.detail_view}', ${n[cellClick.id_key || idKey]})"`
                : '';
            html += `<td${rs}${cs} style="background-color:${bgColor}; color:${textColor};" `
                  + `title="${title}" ${clickAttr}>`
                  + `${n[labelKey]}</td>`;
        });

        // Value column: use the leaf node's value
        const leaf = row[row.length - 1].node;
        const ageMa = leaf[valueCol.key] != null ? leaf[valueCol.key] : '';
        html += `<td class="ics-age">${ageMa}</td>`;

        html += '</tr>';
    });

    html += '</tbody></table>';
    return html;
}

/**
 * Load tree from manifest source_query (flat data → client-side tree)
 */
async function loadTree() {
    const container = document.getElementById('tree-container');

    try {
        // Use manifest source_query if available, otherwise fallback
        let tree;
        const viewDef = manifest && manifest.views && currentTreeViewKey && manifest.views[currentTreeViewKey];
        if (viewDef && viewDef.source_query && viewDef.hierarchy_options) {
            const rows = await fetchQuery(viewDef.source_query);
            tree = buildHierarchy(rows, viewDef.hierarchy_options);
        } else {
            throw new Error('No manifest tree definition found');
        }
        container.innerHTML = '';

        tree.forEach(node => {
            container.appendChild(createTreeNode(node));
        });
    } catch (error) {
        container.innerHTML = `<div class="text-danger">Error loading tree: ${error.message}</div>`;
    }
}

/**
 * Create tree node element recursively (manifest-driven)
 */
function createTreeNode(node) {
    const div = document.createElement('div');
    div.className = 'tree-node';

    const viewDef = manifest && manifest.views && currentTreeViewKey && manifest.views[currentTreeViewKey];
    const hOpts = (viewDef && viewDef.hierarchy_options) || {};
    const tOpts = (viewDef && viewDef.tree_display) || {};
    const leafRank = tOpts.leaf_rank || null;
    const rankKey = hOpts.rank_key || 'rank';
    const labelKey = hOpts.label_key || 'name';
    const countKey = tOpts.count_key || null;
    const idKey = hOpts.id_key || 'id';

    const hasChildren = node.children && node.children.length > 0;
    const isLeaf = node[rankKey] === leafRank;

    // Node content
    const content = document.createElement('div');
    content.className = `tree-node-content rank-${node[rankKey]}`;
    content.dataset.id = node[idKey];
    content.dataset.rank = node[rankKey];
    content.dataset.name = node[labelKey];

    // Toggle icon
    const toggle = document.createElement('span');
    toggle.className = 'tree-toggle';
    if (hasChildren) {
        toggle.innerHTML = '<i class="bi bi-chevron-down"></i>';
    }
    content.appendChild(toggle);

    // Folder/File icon
    const icon = document.createElement('span');
    icon.className = 'tree-icon';
    if (isLeaf) {
        icon.innerHTML = '<i class="bi bi-folder-fill"></i>';
    } else {
        icon.innerHTML = '<i class="bi bi-folder2"></i>';
    }
    content.appendChild(icon);

    // Label
    const label = document.createElement('span');
    label.className = 'tree-label';
    label.textContent = node[labelKey];
    content.appendChild(label);

    // Count (for leaf nodes)
    if (isLeaf && node[countKey] > 0) {
        const count = document.createElement('span');
        count.className = 'tree-count';
        count.textContent = `(${node[countKey]})`;
        content.appendChild(count);
    }

    // Info icon — detail view from manifest
    const infoBtn = document.createElement('span');
    infoBtn.className = 'tree-info';
    infoBtn.innerHTML = '<i class="bi bi-info-circle"></i>';
    infoBtn.title = 'View details';
    infoBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const infoOpts = tOpts.on_node_info || {};
        if (infoOpts.detail_view) {
            openDetail(infoOpts.detail_view, node[infoOpts.id_key || idKey]);
        }
    });
    content.appendChild(infoBtn);

    // Click handler
    content.addEventListener('click', (e) => {
        if (hasChildren) {
            // Toggle children visibility
            const children = div.querySelector('.tree-children');
            if (children) {
                children.classList.toggle('collapsed');
                const chevron = toggle.querySelector('i');
                chevron.className = children.classList.contains('collapsed')
                    ? 'bi bi-chevron-right'
                    : 'bi bi-chevron-down';
            }
        }

        if (isLeaf) {
            selectTreeLeaf(node[idKey], node[labelKey]);
        }
    });

    div.appendChild(content);

    // Children container
    if (hasChildren) {
        const childrenDiv = document.createElement('div');
        childrenDiv.className = 'tree-children';

        node.children.forEach(child => {
            childrenDiv.appendChild(createTreeNode(child));
        });

        div.appendChild(childrenDiv);
    }

    return div;
}

/**
 * Select a tree leaf node and load its items (manifest-driven)
 */
async function selectTreeLeaf(leafId, leafName) {
    // Update selection highlight
    document.querySelectorAll('.tree-node-content.selected').forEach(el => {
        el.classList.remove('selected');
    });
    document.querySelector(`.tree-node-content[data-id="${leafId}"]`)?.classList.add('selected');

    selectedLeafId = leafId;

    const viewDef = manifest && manifest.views && currentTreeViewKey && manifest.views[currentTreeViewKey];
    const tOpts = (viewDef && viewDef.tree_display) || {};
    const filterDef = tOpts.item_valid_filter || {};
    const hasFilterDef = filterDef.key ? true : false;

    // Update header with filter checkbox (only if filter is defined)
    const header = document.getElementById('list-header');
    const filterHtml = hasFilterDef ? `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="validOnlyCheck"
                       ${showOnlyValid ? 'checked' : ''} onchange="toggleValidFilter()">
                <label class="form-check-label" for="validOnlyCheck">${filterDef.label || 'Valid only'}</label>
            </div>` : '';
    header.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="bi bi-folder-fill"></i> ${leafName}</h5>
            ${filterHtml}
        </div>`;

    // Load items via named query from manifest
    const container = document.getElementById('list-container');
    container.innerHTML = '<div class="loading">Loading...</div>';

    try {
        let items;
        if (tOpts.item_query && tOpts.item_param) {
            const baseUrl = `/api/queries/${tOpts.item_query}/execute`;
            const url = `${baseUrl}?${tOpts.item_param}=${leafId}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load items');
            const data = await response.json();
            items = data.rows;
        } else {
            throw new Error('No manifest item query defined');
        }

        currentItems = items;  // Store for filtering
        renderTreeItemTable();

    } catch (error) {
        container.innerHTML = `<div class="text-danger">Error loading items: ${error.message}</div>`;
    }
}


/**
 * Toggle valid-only filter
 */
function toggleValidFilter() {
    showOnlyValid = document.getElementById('validOnlyCheck').checked;
    renderTreeItemTable();
}

/**
 * Render tree leaf item table with current filter (manifest-driven columns)
 */
function renderTreeItemTable() {
    const container = document.getElementById('list-container');

    const viewDef = manifest && manifest.views && currentTreeViewKey && manifest.views[currentTreeViewKey];
    const hOpts = (viewDef && viewDef.hierarchy_options) || {};
    const tOpts = (viewDef && viewDef.tree_display) || {};
    const filterDef = tOpts.item_valid_filter || {};
    const filterKey = filterDef.key || null;
    const columns = tOpts.item_columns || [
        {key: 'name', label: 'Name'},
        {key: 'id', label: 'ID'}
    ];
    const clickDef = tOpts.on_item_click || {id_key: 'id'};
    const idKey = hOpts.id_key || 'id';

    const hasFilter = filterKey && currentItems.some(g => filterKey in g);
    const items = (hasFilter && showOnlyValid)
        ? currentItems.filter(g => g[filterKey])
        : currentItems;

    if (items.length === 0) {
        const message = hasFilter && showOnlyValid && currentItems.length > 0
            ? `No valid items (${currentItems.length} invalid)`
            : 'No items found';
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-inbox"></i>
                <p>${message}</p>
            </div>`;
        return;
    }

    // Count stats
    let html = '';
    if (hasFilter) {
        const validCount = currentItems.filter(g => g[filterKey]).length;
        const invalidCount = currentItems.length - validCount;
        const statsText = showOnlyValid
            ? `Showing ${validCount} valid` + (invalidCount > 0 ? ` (${invalidCount} invalid hidden)` : '')
            : `Showing all ${currentItems.length} (${validCount} valid, ${invalidCount} invalid)`;
        html += `<div class="item-stats text-muted mb-2">${statsText}</div>`;
    } else {
        html += `<div class="item-stats text-muted mb-2">${items.length} items</div>`;
    }

    html += '<table class="item-table"><thead><tr>';
    columns.forEach(col => { html += `<th>${col.label}</th>`; });
    html += '</tr></thead><tbody>';

    items.forEach(g => {
        const rowClass = (hasFilter && !g[filterKey]) ? 'invalid' : '';
        const detailView = clickDef.detail_view;
        const clickAttr = detailView
            ? `onclick="openDetail('${detailView}', ${g[clickDef.id_key || idKey]})"`
            : '';
        html += `<tr class="${rowClass}" ${clickAttr}>`;
        columns.forEach(col => {
            let val = g[col.key];
            if (col.truncate && val) val = truncate(val, col.truncate);
            if (col.type === 'boolean' || col.format === 'boolean') {
                val = val ? (col.true_label || BOOLEAN_TRUE_LABEL) : (col.false_label || BOOLEAN_FALSE_LABEL);
            } else if (val == null) {
                val = '';
            }
            if (col.italic) {
                html += `<td class="item-name"><i>${val}</i></td>`;
            } else {
                html += `<td>${val}</td>`;
            }
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

/**
 * Expand tree path to a specific node and highlight it
 */
function expandTreeToNode(nodeId) {
    const nodeContent = document.querySelector(`.tree-node-content[data-id="${nodeId}"]`);
    if (!nodeContent) return;

    // Walk up DOM to expand all collapsed parent containers
    let element = nodeContent.parentElement;
    while (element) {
        if (element.classList && element.classList.contains('tree-children') && element.classList.contains('collapsed')) {
            element.classList.remove('collapsed');
            const parentContent = element.previousElementSibling;
            if (parentContent) {
                const chevron = parentContent.querySelector('.tree-toggle i');
                if (chevron) chevron.className = 'bi bi-chevron-down';
            }
        }
        element = element.parentElement;
    }

    // Highlight the node
    document.querySelectorAll('.tree-node-content.selected').forEach(el => {
        el.classList.remove('selected');
    });
    nodeContent.classList.add('selected');
    nodeContent.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Expand all tree nodes
 */
function expandAll() {
    document.querySelectorAll('.tree-children.collapsed').forEach(el => {
        el.classList.remove('collapsed');
    });
    document.querySelectorAll('.tree-toggle i').forEach(el => {
        el.className = 'bi bi-chevron-down';
    });
}

/**
 * Collapse all tree nodes
 */
function collapseAll() {
    document.querySelectorAll('.tree-children').forEach(el => {
        el.classList.add('collapsed');
    });
    document.querySelectorAll('.tree-toggle i').forEach(el => {
        el.className = 'bi bi-chevron-right';
    });
}

/**
 * Build temporal range HTML.
 * Reads link target from field.link.detail_view and mapping data key from
 * field.mapping_key — all manifest-driven, no hardcoded domain knowledge.
 */
function buildTemporalRangeHTML(field, data) {
    const code = resolveDataPath(data, field.key);
    if (!code) return '-';
    let html = `<code>${code}</code>`;
    const mappingKey = field.mapping_key;
    const detailView = field.link && field.link.detail_view;
    if (mappingKey && detailView) {
        const mapping = resolveDataPath(data, mappingKey);
        if (mapping && Array.isArray(mapping) && mapping.length > 0) {
            const links = mapping.map(m =>
                `<a class="detail-link" onclick="openDetail('${detailView}', ${m.id})">${m.name}</a>` +
                (m.mapping_type && m.mapping_type !== 'exact' ? ` <small class="text-muted">(${m.mapping_type})</small>` : '')
            ).join(', ');
            html += ` &rarr; ${links}`;
        }
    }
    return html;
}

/**
 * Build hierarchy HTML.
 * Reads link target from field.link.detail_view and data key from field.data_key
 * — all manifest-driven, no hardcoded domain knowledge.
 */
function buildHierarchyHTML(field, data) {
    const dataKey = field.data_key || field.key;
    const arr = resolveDataPath(data, dataKey);
    if (arr && Array.isArray(arr) && arr.length > 0) {
        const detailView = field.link && field.link.detail_view;
        return arr.map(h => {
            if (detailView && h.id != null) {
                return `<a class="detail-link" onclick="openDetail('${detailView}', ${h.id})">${h.name}</a>`;
            }
            return h.name || h;
        }).join(' &rarr; ');
    }
    return '-';
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

/**
 * Build the static HTML for the annotation section (form + placeholder for list)
 */
function buildAnnotationSectionHTML(entityType, entityId) {
    return `
        <div class="annotation-section" id="annotation-section-${entityType}-${entityId}">
            <h6>My Notes</h6>
            <div id="annotation-list-${entityType}-${entityId}">
                <div class="loading">Loading notes...</div>
            </div>
            <div class="annotation-form mt-2">
                <div class="mb-2">
                    <select class="form-select form-select-sm" id="annotation-type-${entityType}-${entityId}">
                        <option value="note">Note</option>
                        <option value="correction">Correction</option>
                        <option value="alternative">Alternative</option>
                        <option value="link">Link</option>
                    </select>
                </div>
                <div class="mb-2">
                    <textarea class="form-control form-control-sm" id="annotation-content-${entityType}-${entityId}"
                              rows="2" placeholder="Add a note..."></textarea>
                </div>
                <div class="d-flex gap-2">
                    <input type="text" class="form-control form-control-sm" id="annotation-author-${entityType}-${entityId}"
                           placeholder="Author (optional)" style="max-width: 200px;">
                    <button class="btn btn-sm btn-outline-primary"
                            onclick="addAnnotation('${entityType}', ${entityId})">Add</button>
                </div>
            </div>
        </div>`;
}

/**
 * Load annotations for an entity and render them
 */
async function loadAnnotations(entityType, entityId) {
    const listContainer = document.getElementById(`annotation-list-${entityType}-${entityId}`);
    if (!listContainer) return;

    try {
        const annUrl = `/api/annotations/${entityType}/${entityId}`;
        const response = await fetch(annUrl);
        const annotations = await response.json();

        if (annotations.length === 0) {
            listContainer.innerHTML = '<p class="text-muted mb-0" style="font-size:0.85rem;">No notes yet.</p>';
            return;
        }

        let html = '';
        annotations.forEach(a => {
            const typeBadge = {
                'note': 'bg-info',
                'correction': 'bg-warning text-dark',
                'alternative': 'bg-success',
                'link': 'bg-primary'
            }[a.annotation_type] || 'bg-secondary';

            html += `
                <div class="annotation-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <span class="badge ${typeBadge}" style="font-size:0.7rem;">${a.annotation_type}</span>
                            ${a.author ? `<small class="text-muted ms-1">${a.author}</small>` : ''}
                            <small class="text-muted ms-1">${a.created_at}</small>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" style="padding:0 4px; font-size:0.7rem;"
                                onclick="deleteAnnotation(${a.id}, '${entityType}', ${entityId})">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                    <div style="margin-top:4px; font-size:0.9rem;">${a.content}</div>
                </div>`;
        });

        listContainer.innerHTML = html;
    } catch (error) {
        listContainer.innerHTML = `<div class="text-danger" style="font-size:0.85rem;">Error loading notes.</div>`;
    }
}

/**
 * Add a new annotation
 */
async function addAnnotation(entityType, entityId) {
    const contentEl = document.getElementById(`annotation-content-${entityType}-${entityId}`);
    const typeEl = document.getElementById(`annotation-type-${entityType}-${entityId}`);
    const authorEl = document.getElementById(`annotation-author-${entityType}-${entityId}`);

    const content = contentEl.value.trim();
    if (!content) return;

    try {
        const postUrl = '/api/annotations';
        const response = await fetch(postUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                entity_type: entityType,
                entity_id: entityId,
                annotation_type: typeEl.value,
                content: content,
                author: authorEl.value.trim() || null
            })
        });

        if (response.ok) {
            contentEl.value = '';
            loadAnnotations(entityType, entityId);
        }
    } catch (error) {
        // Silent fail
    }
}

/**
 * Delete an annotation
 */
async function deleteAnnotation(annotationId, entityType, entityId) {
    try {
        const delUrl = `/api/annotations/${annotationId}`;
        const response = await fetch(delUrl, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadAnnotations(entityType, entityId);
        }
    } catch (error) {
        // Silent fail
    }
}


// ═══════════════════════════════════════════════════════════════════════
// Generic Manifest-Driven Detail Renderer (Phase 39)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Open a detail view by manifest key. Falls back to auto-detail if view is missing.
 */
async function openDetail(viewKey, entityId) {
    if (manifest && manifest.views[viewKey]) {
        await renderDetailFromManifest(viewKey, entityId);
    } else if (viewKey.endsWith('_detail')) {
        const table = viewKey.replace('_detail', '');
        await renderAutoDetail(table, entityId);
    }
}

/**
 * Render an auto-generated detail modal for a table row (fallback when no manifest detail view).
 */
async function renderAutoDetail(table, entityId) {
    const modalBody = document.getElementById('detailModalBody');
    const modalTitle = document.getElementById('detailModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    detailModal.show();

    try {
        const response = await fetch(`/api/auto/detail/${table}?id=${entityId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        modalTitle.textContent = data.name || data.title || data.code || `${table} #${entityId}`;

        let html = '<div class="row g-2">';
        for (const [key, value] of Object.entries(data)) {
            if (value == null) continue;
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            html += `<div class="col-md-4 fw-bold text-muted">${label}</div>`;
            html += `<div class="col-md-8">${value}</div>`;
        }
        html += '</div>';
        modalBody.innerHTML = html;
    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error loading details: ${error.message}</div>`;
    }
}

/**
 * Resolve a dotted path (e.g., "parent.name") on a data object.
 */
function resolveDataPath(data, path) {
    if (!data || !path) return undefined;
    return path.split('.').reduce((obj, key) => (obj != null ? obj[key] : undefined), data);
}

/**
 * Check a condition against data. Supports:
 *  - string key: truthy check (arrays check length > 0)
 *  - falsy/missing condition: always true
 */
function checkCondition(data, condition) {
    if (!condition) return true;
    const val = resolveDataPath(data, condition);
    if (Array.isArray(val)) return val.length > 0;
    return !!val;
}

/**
 * Build the modal title from a title_template and data.
 */
function buildDetailTitle(template, data) {
    if (!template || !template.format) return data.name || '';
    let title = template.format;
    // Replace {icon} with Bootstrap icon
    if (template.icon) {
        title = title.replace('{icon}', `<i class="bi ${template.icon}"></i>`);
    } else {
        title = title.replace('{icon}', '');
    }
    // Replace {field} placeholders
    title = title.replace(/\{(\w+)\}/g, (match, key) => {
        const val = data[key];
        return (val != null && val !== '') ? val : '';
    });
    return title.trim();
}

/**
 * Compute a derived value. Built-in compute functions.
 */
function computeValue(computeName, data, row) {
    const src = row || data;
    switch (computeName) {
        case 'time_range':
            if (src.start_mya != null && src.end_mya != null)
                return `${src.start_mya} — ${src.end_mya} Ma`;
            return '-';
        default:
            return '-';
    }
}

/**
 * Format a cell value according to field definition.
 */
function formatFieldValue(field, value, data) {
    const fmt = field.format;

    if (fmt === 'computed') {
        value = computeValue(field.compute, data);
    }

    if (value == null || value === '') {
        // For boolean, treat null/undefined as false
        if (fmt === 'boolean') return field.false_label || BOOLEAN_FALSE_LABEL;
        return '-';
    }

    switch (fmt) {
        case 'italic':
            return `<i>${value}</i>`;
        case 'boolean': {
            const cls = value ? '' : (field.false_class || '');
            const label = value ? (field.true_label || BOOLEAN_TRUE_LABEL) : (field.false_label || BOOLEAN_FALSE_LABEL);
            return cls ? `<span class="${cls}">${label}</span>` : label;
        }
        case 'link': {
            const linkDef = field.link;
            if (!linkDef) return value;
            const linkId = resolveDataPath(data, linkDef.id_path || linkDef.id_key);
            if (linkId == null) return value;
            return `<a class="detail-link" onclick="openDetail('${linkDef.detail_view}', ${linkId})">${value}</a>`;
        }
        case 'color_chip':
            return `<span class="color-chip" style="background-color:${value}"></span> ${value}`;
        case 'code':
            return `<code>${value}</code>`;
        case 'hierarchy':
            return buildHierarchyHTML(field, data);
        case 'temporal_range':
            return buildTemporalRangeHTML(field, data);
        case 'computed':
            return value; // already computed above
        default:
            return value;
    }
}

/**
 * Render a field_grid section.
 */
function renderFieldGrid(section, data) {
    const fields = section.fields || [];
    let gridHtml = '';

    for (const field of fields) {
        // Per-field condition check
        if (field.condition && !checkCondition(data, field.condition)) continue;

        let value = resolveDataPath(data, field.key);
        let formatted = formatFieldValue(field, value, data);

        // Suffix support (e.g., year + year_suffix)
        if (field.suffix_key) {
            const suffix = resolveDataPath(data, field.suffix_key);
            if (suffix) {
                if (field.suffix_format) {
                    formatted += ` <small class="text-muted">${field.suffix_format.replace('{value}', suffix)}</small>`;
                } else {
                    formatted += suffix;
                }
            }
        }

        gridHtml += `
            <span class="detail-label">${field.label}:</span>
            <span class="detail-value">${formatted}</span>`;
    }

    if (!gridHtml) return '';
    const titleHtml = section.title ? `<h6>${section.title}</h6>` : '';
    return `
        <div class="detail-section">
            ${titleHtml}
            <div class="detail-grid">${gridHtml}
            </div>
        </div>`;
}

/**
 * Render a linked_table section.
 */
function renderLinkedTable(section, data) {
    const rows = data[section.data_key] || [];
    const columns = section.columns || [];
    const onClick = section.on_row_click;
    const title = section.title ? section.title.replace('{count}', rows.length) : '';
    const titleHtml = title ? `<h6>${title}</h6>` : '';

    // Empty handling
    if (rows.length === 0) {
        if (section.show_empty) {
            return `
                <div class="detail-section">
                    ${titleHtml}
                    <p class="text-muted">${section.empty_message || 'No data.'}</p>
                </div>`;
        }
        return '';
    }

    // Header
    let html = `
        <div class="detail-section">
            ${titleHtml}
            <div class="detail-list">
                <table class="manifest-table">
                    <thead><tr>`;
    columns.forEach(col => {
        let label = col.label;
        if (col.label_map && rows.length > 0) {
            const values = new Set(rows.map(r => r[col.label_map.key]));
            if (values.size === 1) {
                label = col.label_map.map[values.values().next().value] || label;
            }
        }
        html += `<th>${label}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Rows
    rows.forEach(row => {
        const clickAttr = onClick
            ? ` onclick="openDetail('${onClick.detail_view}', ${row[onClick.id_key]})"`
            : '';
        html += `<tr${clickAttr}>`;

        columns.forEach(col => {
            let val = (col.format === 'computed')
                ? computeValue(col.compute, data, row)
                : row[col.key];

            // Column-level link (e.g., link within item table)
            if (col.link && val) {
                const linkId = row[col.link.id_key];
                if (linkId != null) {
                    val = `<a class="detail-link" onclick="event.stopPropagation(); openDetail('${col.link.detail_view}', ${linkId})">${val}</a>`;
                }
            } else if (col.format === 'boolean') {
                val = val ? (col.true_label || BOOLEAN_TRUE_LABEL) : (col.false_label || BOOLEAN_FALSE_LABEL);
            } else if (col.format === 'color_chip') {
                val = val ? `<span class="color-chip" style="background-color:${val}"></span> ${val}` : '';
            } else if (col.format === 'code') {
                val = val ? `<code>${val}</code>` : '';
            } else if (col.italic) {
                val = val ? `<i>${val}</i>` : '';
            } else {
                val = val != null ? val : '';
            }

            html += `<td>${val}</td>`;
        });

        html += '</tr>';
    });

    html += '</tbody></table></div></div>';
    return html;
}

/**
 * Render a tagged_list section (badge + text items).
 */
function renderTaggedList(section, data) {
    const items = data[section.data_key] || [];
    if (items.length === 0) return '';

    const titleHtml = section.title ? `<h6>${section.title}</h6>` : '';
    let html = `
        <div class="detail-section">
            ${titleHtml}
            <ul class="list-unstyled">`;

    items.forEach(item => {
        const badge = item[section.badge_key] || '';
        const text = item[section.text_key] || '';
        const badgeHtml = section.badge_format === 'code'
            ? `<code>${badge}</code>`
            : `<span class="badge bg-secondary">${badge}</span>`;
        html += `<li>${badgeHtml} <small class="text-muted ms-1">(${text})</small></li>`;
    });

    html += '</ul></div>';
    return html;
}

/**
 * Render a raw_text section (monospace or paragraph).
 */
function renderRawText(section, data) {
    const value = data[section.data_key];
    if (!value) return '';

    const inner = section.format === 'paragraph'
        ? `<p>${value}</p>`
        : `<div class="raw-entry">${value}</div>`;

    const titleHtml = section.title ? `<h6>${section.title}</h6>` : '';
    return `
        <div class="detail-section">
            ${titleHtml}
            ${inner}
        </div>`;
}

/**
 * Render an annotations section (My Notes with CRUD).
 */
function renderAnnotationsSection(section, data) {
    let entityType;
    if (section.entity_type) {
        entityType = section.entity_type;
    } else if (section.entity_type_from) {
        entityType = (data[section.entity_type_from] || '').toLowerCase();
    }
    if (!entityType) return '';
    return buildAnnotationSectionHTML(entityType, data.id);
}

/**
 * Dispatch section rendering by type.
 */
function renderDetailSection(section, data) {
    // Section-level condition check
    if (section.condition && !checkCondition(data, section.condition)) return '';

    switch (section.type) {
        case 'field_grid':      return renderFieldGrid(section, data);
        case 'linked_table':    return renderLinkedTable(section, data);
        case 'tagged_list':     return renderTaggedList(section, data);
        case 'raw_text':        return renderRawText(section, data);
        case 'annotations':     return renderAnnotationsSection(section, data);
        default:
            // Fallback: if section has data_key and data is an array, render as linked_table
            if (section.data_key && Array.isArray(data[section.data_key])) {
                return renderLinkedTable(section, data);
            }
            return '';
    }
}

/**
 * Main entry point: render a detail view from manifest definition.
 */
async function renderDetailFromManifest(viewKey, entityId) {
    const view = manifest.views[viewKey];
    if (!view || view.type !== 'detail') return;

    const modalBody = document.getElementById('detailModalBody');
    const modalTitle = document.getElementById('detailModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    detailModal.show();

    try {
        const url = view.source
            ? view.source.replace('{id}', entityId)
            : `/api/composite/${viewKey}?id=${entityId}`;
        const response = await fetch(url);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${response.status}`);
        }
        const data = await response.json();

        // Title
        modalTitle.innerHTML = buildDetailTitle(view.title_template, data);

        // Sections
        let html = '';
        for (const section of view.sections) {
            html += renderDetailSection(section, data);
        }
        modalBody.innerHTML = html;

        // Post-render: load annotations for any annotations sections
        for (const section of view.sections) {
            if (section.type === 'annotations') {
                let entityType;
                if (section.entity_type) {
                    entityType = section.entity_type;
                } else if (section.entity_type_from) {
                    entityType = (data[section.entity_type_from] || '').toLowerCase();
                }
                if (entityType) {
                    loadAnnotations(entityType, data.id);
                }
            }
        }

    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error loading details: ${error.message}</div>`;
    }
}


// ═══════════════════════════════════════════════════════════════════════
// Global Search (Manifest-Driven)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Build search categories from manifest tab views (non-detail views with source_query + columns).
 */
function buildSearchCategories() {
    if (!manifest || !manifest.views) return [];

    const categories = [];
    for (const [key, view] of Object.entries(manifest.views)) {
        if (view.type === 'detail' || !view.source_query || !view.columns || !view.columns.length) continue;

        categories.push({
            key,
            query: view.source_query,
            label: view.title,
            icon: view.icon || 'bi-square',
            fields: view.columns.map(c => c.key),
            displayField: view.columns[0].key,
            displayItalic: !!view.columns[0].italic,
            metaFields: view.columns.slice(1, 3).map(c => c.key),
            detailView: view.on_row_click ? view.on_row_click.detail_view : null,
            idKey: view.on_row_click ? (view.on_row_click.id_key || 'id') : 'id',
            defaultLimit: 5
        });
    }

    return categories;
}

/**
 * Initialize global search: event listeners, Ctrl+K shortcut, outside click
 */
function initGlobalSearch() {
    const input = document.getElementById('global-search-input');
    const resultsEl = document.getElementById('global-search-results');
    if (!input || !resultsEl) return;

    // Build categories from manifest
    searchCategories = buildSearchCategories();

    // Input event with debounce
    input.addEventListener('input', () => {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            performSearch(input.value);
        }, 200);
    });

    // Keyboard navigation
    input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            moveSearchHighlight(1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            moveSearchHighlight(-1);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            selectSearchHighlight();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            hideSearchResults();
            input.blur();
        }
    });

    // Ctrl+K shortcut
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            input.focus();
            input.select();
        }
    });

    // Outside click closes dropdown
    document.addEventListener('click', (e) => {
        const container = document.querySelector('.global-search-container');
        if (container && !container.contains(e.target)) {
            hideSearchResults();
        }
    });
}

/**
 * Preload search index: fetch all category queries in parallel
 */
async function preloadSearchIndex() {
    if (searchIndex || searchIndexLoading) return;
    if (searchCategories.length === 0) return;
    searchIndexLoading = true;

    searchIndex = {};

    const promises = searchCategories.map(async (cat) => {
        try {
            const rows = await fetchQuery(cat.query);

            // Pre-compute _searchText for fast matching
            rows.forEach(row => {
                row._searchText = cat.fields
                    .map(f => (row[f] || ''))
                    .join(' ')
                    .toLowerCase();
            });

            searchIndex[cat.key] = rows;
        } catch (e) {
            searchIndex[cat.key] = [];
        }
    });

    await Promise.all(promises);
    searchIndexLoading = false;
}

/**
 * Perform search across all categories
 */
function performSearch(query) {
    const resultsEl = document.getElementById('global-search-results');
    if (!resultsEl) return;

    query = (query || '').trim();

    if (query.length < 2) {
        hideSearchResults();
        return;
    }

    // Show loading if index not ready
    if (!searchIndex) {
        resultsEl.innerHTML = '<div class="search-status"><i class="bi bi-hourglass-split"></i> Building search index...</div>';
        resultsEl.classList.add('visible');
        if (!searchIndexLoading) preloadSearchIndex();
        setTimeout(() => performSearch(query), 300);
        return;
    }

    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 0);
    searchResults = [];
    searchHighlightIndex = -1;
    searchExpandedCategories = {};

    let html = '';
    let totalResults = 0;

    searchCategories.forEach(cat => {
        const rows = searchIndex[cat.key] || [];

        // Multi-term AND matching
        let matches = rows.filter(row =>
            terms.every(term => row._searchText.includes(term))
        );

        if (matches.length === 0) return;

        // Sort: prefix match on display field first, then alphabetical
        const firstTerm = terms[0];
        matches.sort((a, b) => {
            const aName = (a[cat.displayField] || '').toLowerCase();
            const bName = (b[cat.displayField] || '').toLowerCase();
            const aPrefix = aName.startsWith(firstTerm) ? 0 : 1;
            const bPrefix = bName.startsWith(firstTerm) ? 0 : 1;
            if (aPrefix !== bPrefix) return aPrefix - bPrefix;
            return aName.localeCompare(bName);
        });

        totalResults += matches.length;

        // Category header
        html += `<div class="search-category-header">
            <i class="bi ${cat.icon}"></i> ${cat.label}
            <span class="search-cat-count">${matches.length}</span>
        </div>`;

        // Show limited results
        const limit = cat.defaultLimit;
        const visible = matches.slice(0, limit);
        const remaining = matches.length - limit;

        visible.forEach(row => {
            const idx = searchResults.length;
            searchResults.push({ cat, row });
            html += renderSearchResultItem(cat, row, terms, idx);
        });

        // "+N more" expander
        if (remaining > 0) {
            const catKey = cat.key;
            html += `<div class="search-more-item" data-cat="${catKey}" onclick="expandSearchCategory('${catKey}', this)">+${remaining} more</div>`;
            searchExpandedCategories[catKey] = { matches: matches.slice(limit), cat, startIdx: searchResults.length };
        }
    });

    if (totalResults === 0) {
        html = '<div class="search-status">No results found</div>';
    }

    resultsEl.innerHTML = html;
    resultsEl.classList.add('visible');
}

/**
 * Render a single search result item
 */
function renderSearchResultItem(cat, row, terms, idx) {
    const displayVal = row[cat.displayField] || '';
    const highlighted = highlightTerms(escapeHtml(displayVal), terms);

    let mainHtml = cat.displayItalic
        ? `<i>${highlighted}</i>`
        : highlighted;

    let metaHtml = '';
    if (cat.metaFields && cat.metaFields.length > 0) {
        const metaParts = cat.metaFields
            .map(f => row[f] || '')
            .filter(v => v)
            .join(', ');
        if (metaParts) {
            const metaText = truncate(metaParts, 60);
            metaHtml = `<span class="search-result-meta">${escapeHtml(metaText)}</span>`;
        }
    }

    const clickable = cat.detailView ? '' : ' style="cursor:default; opacity:0.7;"';

    return `<div class="search-result-item" data-idx="${idx}"
                 onclick="onSearchResultClick(${idx})"
                 onmouseenter="searchHighlightIndex=${idx}; updateSearchHighlight()"${clickable}>
        <span class="search-result-main">${mainHtml}</span>
        ${metaHtml}
    </div>`;
}

/**
 * Highlight search terms in text using <mark> tags
 */
function highlightTerms(escapedText, terms) {
    let result = escapedText;
    terms.forEach(term => {
        const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escaped})`, 'gi');
        result = result.replace(regex, '<mark>$1</mark>');
    });
    return result;
}

/**
 * Expand a "+N more" category to show all results
 */
function expandSearchCategory(catKey, el) {
    const data = searchExpandedCategories[catKey];
    if (!data) return;

    const input = document.getElementById('global-search-input');
    const query = (input ? input.value : '').trim();
    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 0);

    let html = '';
    data.matches.forEach(row => {
        const idx = searchResults.length;
        searchResults.push({ cat: data.cat, row });
        html += renderSearchResultItem(data.cat, row, terms, idx);
    });

    el.insertAdjacentHTML('afterend', html);
    el.remove();
    delete searchExpandedCategories[catKey];
}

/**
 * Handle search result click
 */
function onSearchResultClick(idx) {
    const item = searchResults[idx];
    if (!item || !item.cat.detailView) return;

    hideSearchResults();

    const id = item.row[item.cat.idKey];
    openDetail(item.cat.detailView, id);
}

/**
 * Move highlight up/down
 */
function moveSearchHighlight(delta) {
    if (searchResults.length === 0) return;

    searchHighlightIndex += delta;
    if (searchHighlightIndex < 0) searchHighlightIndex = searchResults.length - 1;
    if (searchHighlightIndex >= searchResults.length) searchHighlightIndex = 0;

    updateSearchHighlight();
}

/**
 * Update highlight visual
 */
function updateSearchHighlight() {
    const resultsEl = document.getElementById('global-search-results');
    if (!resultsEl) return;

    resultsEl.querySelectorAll('.search-result-item').forEach(el => {
        el.classList.toggle('highlighted', parseInt(el.dataset.idx) === searchHighlightIndex);
    });

    // Scroll into view
    const highlighted = resultsEl.querySelector('.search-result-item.highlighted');
    if (highlighted) {
        highlighted.scrollIntoView({ block: 'nearest' });
    }
}

/**
 * Select the currently highlighted result
 */
function selectSearchHighlight() {
    if (searchHighlightIndex >= 0 && searchHighlightIndex < searchResults.length) {
        onSearchResultClick(searchHighlightIndex);
    }
}

/**
 * Hide search results dropdown
 */
function hideSearchResults() {
    const resultsEl = document.getElementById('global-search-results');
    if (resultsEl) {
        resultsEl.classList.remove('visible');
    }
    searchHighlightIndex = -1;
}
