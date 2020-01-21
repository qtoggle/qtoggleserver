/**
 * @namespace qtoggle.dashboard
 */

import Logger from '$qui/lib/logger.module.js'

import StockIcon from '$qui/icons/stock-icon.js'
import {asap}    from '$qui/utils/misc.js'

import * as API from '$app/api.js'


export const WIDGET_ICON = new StockIcon({name: 'widget', stockName: 'qtoggle'})
export const PANEL_ICON = new StockIcon({name: 'panel', stockName: 'qtoggle'})
export const GROUP_ICON = new StockIcon({name: 'panel-group', stockName: 'qtoggle'})

export const logger = Logger.get('qtoggle.dashboard')

let pendingSavePanelsTimeoutHandle = null
let rootGroup = null
let currentPanel = null


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

export function getCurrentPanel() {
    return currentPanel
}

export function setCurrentPanel(panel) {
    currentPanel = panel
}

export function getRootGroup() {
    return rootGroup
}

export function setRootGroup(group) {
    rootGroup = group
}

export function getAllPanels() {
    if (rootGroup) {
        return rootGroup.getPanelsRec()
    }

    return []
}
