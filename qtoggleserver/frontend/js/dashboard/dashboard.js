/**
 * @namespace qtoggle.dashboard
 */

import Logger from '$qui/lib/logger.module.js'

import StockIcon from '$qui/icons/stock-icon.js'

import * as DashboardAPI from '$app/api/dashboard.js'


const PANELS_SAVE_INTERVAL = 2000 /* Milliseconds */


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

let pendingSavePanelsTimeoutHandle = null
let rootGroup = null
let currentPanel = null


/**
 * @alias qtoggle.dashboard.savePanels
 */
export function savePanels() {
    if (pendingSavePanelsTimeoutHandle) {
        clearTimeout(pendingSavePanelsTimeoutHandle)
    }

    pendingSavePanelsTimeoutHandle = setTimeout(function () {

        logger.debug('saving panels')
        pendingSavePanelsTimeoutHandle = null
        let panels = rootGroup.getChildren().map(p => p.toJSON())

        DashboardAPI.putDashboardPanels(panels)

    }, PANELS_SAVE_INTERVAL)
}

/**
 * @alias qtoggle.dashboard.hasPendingSave
 * @returns {Boolean}
 */
export function hasPendingSave() {
    return pendingSavePanelsTimeoutHandle != null
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
