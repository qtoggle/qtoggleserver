/**
 * @namespace qtoggle.dashboard
 */

import Logger from '$qui/lib/logger.module.js'

import StockIcon from '$qui/icons/stock-icon.js'
import {asap}    from '$qui/utils/misc.js'

import * as API from '$app/api.js'


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

    pendingSavePanelsTimeoutHandle = asap(function () {

        logger.debug('saving panels')
        pendingSavePanelsTimeoutHandle = null
        let panels = rootGroup.getChildren().map(p => p.toJSON())

        API.putDashboardPanels(panels)

    })
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
