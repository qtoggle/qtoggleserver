/**
 * @namespace qtoggle.dashboard
 */

import Logger from '$qui/lib/logger.module.js'

import StockIcon        from '$qui/icons/stock-icon.js'
import Debouncer        from '$qui/utils/debouncer.js'
import * as ObjectUtils from '$qui/utils/object.js'

import * as DashboardAPI from '$app/api/dashboard.js'
import * as Cache        from '$app/cache.js'


const PANELS_SAVE_INTERVAL = 2000 /* Milliseconds */
const DEFAULT_PANEL_PREFS_PATH = 'dashboard.default_panel'


/**
 * @alias qtoggle.dashboard.WIDGET_ICON
 * @type {qui.icons.Icon}
 */
export const WIDGET_ICON = new StockIcon({name: 'widget', stockName: 'qtoggle'})

/**
 * @alias qtoggle.dashboard.PANEL_ICON
 * @type {qui.icons.Icon}
 */
export const PANEL_ICON = new StockIcon({name: 'panel', stockName: 'qtoggle'})

/**
 * @alias qtoggle.dashboard.GROUP_ICON
 * @type {qui.icons.Icon}
 */
export const GROUP_ICON = new StockIcon({name: 'panel-group', stockName: 'qtoggle'})

/**
 * @alias qtoggle.dashboard.logger
 * @type {Logger}
 */
export const logger = Logger.get('qtoggle.dashboard')

const savePanelsDebouncer = new Debouncer(() => {
    logger.debug('saving panels')
    let panels = rootGroup.getChildren().map(p => p.toJSON())
    DashboardAPI.putDashboardPanels(panels)
}, PANELS_SAVE_INTERVAL)

let rootGroup = null
let currentPanel = null


/**
 * @alias qtoggle.dashboard.savePanels
 */
export function savePanels() {
    savePanelsDebouncer.call()
}

/**
 * @alias qtoggle.dashboard.hasPendingSave
 * @returns {Boolean}
 */
export function hasPendingSave() {
    return savePanelsDebouncer.isPending()
}

/**
 * @alias qtoggle.dashboard.getCurrentPanel
 * @returns {?qtoggle.dashboard.Panel}
 */
export function getCurrentPanel() {
    return currentPanel
}

/**
 * @alias qtoggle.dashboard.setCurrentPanel
 * @param {?qtoggle.dashboard.Panel} panel
 */
export function setCurrentPanel(panel) {
    currentPanel = panel
}

/**
 * @alias qtoggle.dashboard.getRootGroup
 * @returns {qtoggle.dashboard.Group}
 */
export function getRootGroup() {
    return rootGroup
}

/**
 * @alias qtoggle.dashboard.setRootGroup
 * @param {qtoggle.dashboard.Group} group
 */
export function setRootGroup(group) {
    rootGroup = group
}

/**
 * @alias qtoggle.dashboard.getAllPanels
 * @returns {qtoggle.dashboard.Panel[]}
 */
export function getAllPanels() {
    if (rootGroup) {
        return rootGroup.getPanelsRec()
    }

    return []
}

/**
 * Return the path (list of ids) of the user's default panel, or `null` if not set.
 * @alias qtoggle.dashboard.getDefaultPanelPath
 * @returns {?String[]}
 */
export function getDefaultPanelPath() {
    if (!Cache.whenPrefsCacheReady.isFulfilled()) {
        return null
    }

    return Cache.getPrefs(DEFAULT_PANEL_PREFS_PATH, null)
}

/**
 * @alias qtoggle.dashboard.setDefaultPanelPath
 * @param {?String[]} path
 */
export function setDefaultPanelPath(path) {
    Cache.setPrefs(DEFAULT_PANEL_PREFS_PATH, path)
}

/**
 * Return the user's default panel, or `null` if not set or no longer present.
 * @alias qtoggle.dashboard.getDefaultPanel
 * @returns {?qtoggle.dashboard.Panel}
 */
export function getDefaultPanel() {
    let path = getDefaultPanelPath()
    if (!path) {
        return null
    }

    return getAllPanels().find(p => ObjectUtils.deepEquals(p.getIdPath(), path)) || null
}

/**
 * Keep the default panel path in sync when a panel or group is renamed (`newPath` set) or removed (`newPath` null).
 * @alias qtoggle.dashboard.updateDefaultPanelPath
 * @param {String[]} oldPath
 * @param {?String[]} newPath
 */
export function updateDefaultPanelPath(oldPath, newPath) {
    let path = getDefaultPanelPath()
    if (!path || ObjectUtils.deepEquals(oldPath, newPath)) {
        return
    }

    /* Only act if the default panel is the renamed/removed item or lives under it */
    if (path.length < oldPath.length || oldPath.some((id, i) => path[i] !== id)) {
        return
    }

    setDefaultPanelPath(newPath ? newPath.concat(path.slice(oldPath.length)) : null)
}
