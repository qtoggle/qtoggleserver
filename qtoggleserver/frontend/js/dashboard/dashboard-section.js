
import {gettext}         from '$qui/base/i18n.js'
import * as Toast        from '$qui/messages/toast.js'
import {asap}            from '$qui/utils/misc.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import * as PromiseUtils from '$qui/utils/promise.js'

import * as AuthAPI               from '$app/api/auth.js'
import * as BaseAPI               from '$app/api/base.js'
import * as DashboardAPI          from '$app/api/dashboard.js'
import * as NotificationsAPI      from '$app/api/notifications.js'
import * as Cache                 from '$app/cache.js'
import {getGlobalProgressMessage} from '$app/common/common.js'
import {Section}                  from '$app/sections.js'
import * as Utils                 from '$app/utils.js'

import * as Dashboard   from './dashboard.js'
import Group            from './group.js'
import WidgetConfigForm from './widgets/widget-config-form.js'

import './widgets/all-widgets/all-widgets.js'


const SECTION_ID = 'dashboard'
const SECTION_TITLE = gettext('Dashboard')

const logger = Dashboard.logger


/**
 * @alias qtoggle.dashboard.DashboardSection
 * @extends qtoggle.sections.Section
 */
class DashboardSection extends Section {

    /**
     * @constructs
     */
    constructor() {
        super({
            id: SECTION_ID,
            title: SECTION_TITLE,
            icon: Dashboard.WIDGET_ICON
        })

        this._whenPanelsLoaded = null
        this._panels = null
        this._updateWidgetConfigPortsASAPHandle = null
    }

    preload() {
        return Cache.whenCacheReady.then(function () {

            return this.whenPanelsLoaded()

        }.bind(this))
    }

    canClose() {
        return !Dashboard.hasPendingSave()
    }

    _loadPanels() {
        logger.debug('loading panels')

        let progressMessage = null
        let loadPromise = DashboardAPI.getDashboardPanels().then(function (panels) {

            logger.debug('panels loaded')
            Cache.setLocalStorageCache('dashboard-panels', panels)

            if (this._panels == null) {
                this._panels = panels
            }
            else if (!ObjectUtils.deepEquals(panels, this._panels)) {
                NotificationsAPI.fakeServerEvent('dashboard-update', {panels, load: true})
            }

        }.bind(this)).catch(function (error) {

            logger.errorStack('loading panels failed', error)
            Utils.showToastError(error)

            throw error

        }).finally(function () {

            if (progressMessage) {
                progressMessage.hide()
            }

        })

        if (this._panels == null) {
            let cachedPanels = Cache.getLocalStorageCache('dashboard-panels')
            if (cachedPanels != null) {
                logger.debug('loaded panels from cache')
                this._panels = cachedPanels
                return Promise.resolve()
            }
        }

        progressMessage = getGlobalProgressMessage().show()
        progressMessage.setMessage(gettext('Loading panels...'))
        return loadPromise
    }

    /**
     * Return a promise that resolves as soon as the panels are loaded.
     * @returns {Promise}
     */
    whenPanelsLoaded() {
        if (!this._whenPanelsLoaded) {
            this._whenPanelsLoaded = this._loadPanels()
        }

        return this._whenPanelsLoaded
    }

    onWindowActiveChange(active) {
        /* Call onPanelBecomeActive on all widgets of current panel */
        let currentPanel = Dashboard.getCurrentPanel()
        if (active && this.isCurrent() && currentPanel) {
            currentPanel.getWidgets().forEach(w => w.onPanelBecomeActive())
        }

        /* Using later() here reduces the chances of request error right when window becomes active */
        PromiseUtils.later(1000).then(() => this._reloadPanelConfig())
    }

    onServerEvent(event) {
        switch (event.type) {
            case 'value-change': {
                let currentPanel = Dashboard.getCurrentPanel()

                if (currentPanel) {
                    currentPanel.getWidgets().forEach(function (widget) {
                        widget.handlePortValueChange(event.params.id, event.params.value)
                    })
                }

                break
            }

            case 'port-update': {
                this._updateWidgetStates()
                this._updateWidgetConfigPorts()

                let currentPanel = Dashboard.getCurrentPanel()
                if (currentPanel) {
                    currentPanel.getWidgets().forEach(function (widget) {
                        widget.handlePortUpdate(event.params)
                    })
                }

                break
            }

            case 'port-add': {
                this._updateWidgetStates()
                this._updateWidgetConfigPorts()

                break
            }

            case 'port-remove': {
                this._updateWidgetStates()
                this._updateWidgetConfigPorts()

                break
            }

            case 'dashboard-update': {
                let source
                if (event.byCurrentSession()) {
                    source = 'current-session'
                }
                else if (event.params['load']) {
                    source = 'load'
                }
                else {
                    source = 'server'
                }
                this._handleDashboardUpdate(event.params['panels'], source)

                break
            }
        }
    }

    onAccessLevelChange(oldLevel, newLevel) {
        /* Update add-enabled flag for all groups */
        let addEnabled = newLevel >= AuthAPI.ACCESS_LEVEL_ADMIN

        function updateGroupRec(group) {
            if (addEnabled) {
                group.enableAdd()
            }
            else {
                group.disableAdd()
            }

            group.getChildren().forEach(function (child) {
                if (child instanceof Group) {
                    updateGroupRec(child)
                }
            })
        }

        if (Dashboard.getRootGroup()) {
            updateGroupRec(Dashboard.getRootGroup())
        }

        /* Update widget editable/protected state */
        this._updateWidgetStates()
    }

    onReset() {
        this._whenPanelsLoaded = null
    }

    onMainDeviceReconnect() {
        /* Call onPanelBecomeActive on all widgets of current panel */
        let currentPanel = Dashboard.getCurrentPanel()
        if (this.isCurrent() && currentPanel) {
            currentPanel.getWidgets().forEach(w => w.onPanelBecomeActive())
        }

        this._reloadPanelConfig()
    }

    _updateWidgetStates() {
        let currentPanel = Dashboard.getCurrentPanel()
        if (!currentPanel) {
            return
        }

        currentPanel.getWidgets().forEach(function (widget) {
            widget.updateState()
        })
    }

    _updateWidgetConfigPorts() {
        if (this._updateWidgetConfigPortsASAPHandle != null) {
            clearTimeout(this._updateWidgetConfigPortsASAPHandle)
        }

        this._updateWidgetConfigPortsASAPHandle = asap(function () {

            this._updateWidgetConfigPortsASAPHandle = null

            let currentPage = this.getCurrentPage()
            if (currentPage instanceof WidgetConfigForm) {
                currentPage.updatePortFields()
            }

        }.bind(this))
    }

    _handleDashboardUpdate(panels, source) {
        let currentPanel = Dashboard.getCurrentPanel()

        this._panels = panels
        Cache.setLocalStorageCache('dashboard-panels', panels)

        logger.info('the dashboard has been updated on the server')

        /* Exit edit mode */
        if (source !== 'current-session' && currentPanel && currentPanel.isEditEnabled()) {
            currentPanel.disableEditing()
        }

        /* Warn user of external edit */
        if (source !== 'current-session') {
            if (this.isCurrent() && source !== 'load') {
                let msg = gettext('The dashboard has been changed.')
                Toast.warning(msg)
            }

            let rootGroup = this.getMainPage()
            if (rootGroup) {
                let promise = Promise.resolve()
                if (rootGroup.getNext()) {
                    promise = rootGroup.getNext().close()
                }

                promise.then(function () {
                    /* Update all groups and panels */
                    rootGroup.fromJSON({children: panels})
                    rootGroup.updateUI(/* recursive = */ true)
                })
            }
        }
    }

    _reloadPanelConfig() {
        /* Reload panels configuration and see if anything has changed */
        logger.debug('reloading panels')
        return DashboardAPI.getDashboardPanels().then(function (panels) {

            logger.debug('panels reloaded')

            if (!ObjectUtils.deepEquals(this._panels, panels)) {
                logger.debug('panels have been updated since last server connection')
                NotificationsAPI.fakeServerEvent('dashboard-update', {panels})
            }

        }.bind(this)).catch(function (error) {

            logger.errorStack('loading panels failed', error)
            Utils.showToastError(error)

        })
    }

    makeMainPage() {
        let rootGroup = new Group({
            name: gettext('Panels')
        })

        Dashboard.setRootGroup(rootGroup)

        /* At this point we can be sure that this._panels has been properly loaded */
        rootGroup.fromJSON({children: this._panels})
        rootGroup.updateUI(/* recursive = */ true)

        return rootGroup
    }

}


export default DashboardSection
