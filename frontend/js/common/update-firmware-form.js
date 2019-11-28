
import $      from '$qui/lib/jquery.module.js'
import Logger from '$qui/lib/logger.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields.js'
import {TextField}       from '$qui/forms/common-fields.js'
import {PageForm}        from '$qui/forms/common-forms.js'
import FormButton        from '$qui/forms/form-button.js'
import FormField         from '$qui/forms/form-field.js'
import {ValidationError} from '$qui/forms/forms.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Toast        from '$qui/messages/toast.js'
import * as PromiseUtils from '$qui/utils/promise.js'
import * as Window       from '$qui/window.js'

import * as API   from '$app/api.js'
import * as Cache from '$app/cache.js'


const FIRMWARE_ICON = new StockIcon({name: 'firmware', stockName: 'qtoggle'})
const FIRMWARE_STATUS_UPTODATE = 'uptodate'
const FIRMWARE_STATUS_UPDATABLE = 'updatable'
const FIRMWARE_STATUS_NOT_AVAILABLE = 'not-available'
const POLLING_INTERVAL = 1

const PRETTY_STATUSES = {
    [FIRMWARE_STATUS_UPDATABLE]: gettext('newer version available'),
    [FIRMWARE_STATUS_UPTODATE]: gettext('up to date'),
    [FIRMWARE_STATUS_NOT_AVAILABLE]: gettext('not available'),
    [API.FIRMWARE_STATUS_CHECKING]: gettext('checking'),
    [API.FIRMWARE_STATUS_DOWNLOADING]: gettext('downloading'),
    [API.FIRMWARE_STATUS_VALIDATING]: gettext('validating'),
    [API.FIRMWARE_STATUS_EXTRACTING]: gettext('extracting'),
    [API.FIRMWARE_STATUS_FLASHING]: gettext('flashing'),
    [API.FIRMWARE_STATUS_RESTARTING]: gettext('restarting'),
    [API.FIRMWARE_STATUS_ERROR]: gettext('an error occurred')
}

const logger = Logger.get('qtoggle.common.updatefirmware')


/**
 * @class StatusField
 * @extends qui.forms.FormField
 * @param {Object} attributes
 */
class StatusField extends FormField {

    constructor({...params}) {
        super(params)

        this._progress = null
        this._icon = null
        this._messageSpan = null
        this._statusValue = null
    }

    makeWidget() {
        let div = $('<div class="devices-update-firmware-status"></div>')

        this._icon = $('<div class="qui-icon"></div>')

        this._progress = $('<div class="progress"></div>')
        this._progress.progressdisc()

        this._messageSpan = $('<span class="label"></span>')

        div.append(this._progress)
        div.append(this._icon)
        div.append(this._messageSpan)

        return div
    }

    valueToWidget(value) {
        let prettyValue = PRETTY_STATUSES[value] || value

        if (value === FIRMWARE_STATUS_UPDATABLE ||
            value === FIRMWARE_STATUS_UPTODATE ||
            value === FIRMWARE_STATUS_NOT_AVAILABLE ||
            value === API.FIRMWARE_STATUS_ERROR) {

            this._progress.progressdisc('setValue', 0)
            this._progress.css('display', 'none')
            this._icon.css('display', '')
            this._messageSpan.html(prettyValue)

            if (value === FIRMWARE_STATUS_UPTODATE) {
                new StockIcon({
                    name: 'check', variant: 'green'
                }).applyTo(this._icon)
            }
            else if (value === FIRMWARE_STATUS_UPDATABLE) {
                new StockIcon({
                    name: 'sync', variant: 'highlight'
                }).applyTo(this._icon)
            }
            else if (value === FIRMWARE_STATUS_NOT_AVAILABLE) {
                new StockIcon({
                    name: 'qmark', variant: 'foreground'
                }).applyTo(this._icon)
            }
            else if (value === API.FIRMWARE_STATUS_ERROR) {
                new StockIcon({
                    name: 'exclam', variant: 'error'
                }).applyTo(this._icon)
            }
        }
        else {
            this._progress.progressdisc('setValue', -1)
            this._progress.css('display', '')
            this._icon.css('display', 'none')
            this._messageSpan.html(`${prettyValue}...`)
        }

        this._statusValue = value
    }

    widgetToValue() {
        return this._statusValue
    }

    setWidgetReadonly(readonly) {
    }

    enableWidget() {
    }

    disableWidget() {
    }

}

/**
 * @class QToggle.Common.UpdateFirmwareForm
 * @extends qui.forms.PageForm
 * @param {String} deviceName
 */
export default class UpdateFirmwareForm extends PageForm {

    constructor(deviceName) {
        super({
            icon: FIRMWARE_ICON,
            title: gettext('Update Firmware'),
            pathId: 'firmware',
            closeOnApply: false,
            continuousValidation: true,

            fields: [
                new TextField({
                    name: 'currentVersion',
                    label: gettext('Current Version'),
                    readonly: true
                }),
                new StatusField({
                    name: 'status',
                    label: gettext('Status')
                }),
                new TextField({
                    name: 'latestVersion',
                    label: gettext('Latest Version'),
                    separator: true,
                    readonly: true
                }),
                new TextField({
                    name: 'releaseDate',
                    label: gettext('Release Date'),
                    readonly: true
                }),
                new CheckField({
                    name: 'advanced',
                    label: gettext('Advanced'),
                    onChange: (advanced, form) => form.updateUI()
                }),
                new TextField({
                    name: 'version',
                    label: gettext('Version'),
                    hidden: true,
                    continuousChange: true
                }),
                new TextField({
                    name: 'url',
                    label: 'URL',
                    hidden: true,
                    continuousChange: true
                })
            ],
            buttons: [
                new FormButton({id: 'close', caption: gettext('Close'), cancel: true}),
                new FormButton({id: 'update', caption: gettext('Update'), style: 'danger', def: true})
            ]
        })

        this._deviceName = deviceName
        this._updateRunning = false
        this._updateFinished = false
    }

    load() {
        if (this.deviceIsSlave()) {
            API.setSlave(this.getDeviceName())
        }

        return this.fetchUpdateStatus().then(function (running) {

            if (running) {
                /* Start polling, but do not chain it to load promise */
                this.pollStatus(POLLING_INTERVAL * 1000)
            }

        }.bind(this)).catch(function (error) {

            logger.errorStack(`failed to get current firmware for device "${this.getDeviceName()}"`, error)
            this.setData({status: API.FIRMWARE_STATUS_ERROR})

            PromiseUtils.asap().then(function () {

                this.setError(error)

            }.bind(this))

        }.bind(this))
    }

    updateUI() {
        let urlField = this.getField('url')
        let versionField = this.getField('version')
        let data = this.getUnvalidatedData()

        if (data.advanced) {
            urlField.show()
            versionField.show()
        }
        else {
            urlField.hide()
            versionField.hide()
        }
    }

    validate(data) {
        if (data.advanced) {
            if (!data.url && !data.version) {
                throw new ValidationError(gettext('Either a version or a URL must be given!'))
            }
            if (data.url && data.version) {
                throw new ValidationError(gettext('Version and URL cannot be both given!'))
            }
        }
        else {
            if (data.status !== FIRMWARE_STATUS_UPDATABLE && data.status !== API.FIRMWARE_STATUS_ERROR) {
                throw new ValidationError() /* To simply disable the update button */
            }
            if (!data.latestVersion) {
                throw new ValidationError() /* To simply disable the update button */
            }
        }
    }

    applyData(data) {
        let version = null
        let url = null
        let deviceName = this.getDeviceName()

        if (data.advanced) {
            if (data.url) {
                logger.debug(`updating device "${deviceName}" firmware from URL ${data.url}`)
                url = data.url
            }
            else { /* Assuming version */
                logger.debug(`updating device "${deviceName}" firmware to version ${data.version}`)
                version = data.version
            }
        }
        else {
            logger.debug(`updating device "${deviceName}" firmware to version ${data.latestVersion}`)
            version = data.latestVersion
        }

        let overrideOffline = false
        if (this.deviceIsSlave()) {
            API.setSlave(deviceName)
            overrideOffline = true
        }

        return API.patchFirmware(version, url, overrideOffline).then(function () {

            if (!this.deviceIsSlave()) {
                this.setModal(true)
                this.getButton('close').disable()
            }

            this._updateRunning = true

        }.bind(this)).then(function () {

            return this.pollStatus()

        }.bind(this)).catch(function (error) {

            logger.errorStack(`failed to update device "${deviceName}" firmware`, error)
            throw error

        })
    }

    fetchUpdateStatus() {
        let overrideOffline = false
        if (this.deviceIsSlave()) {
            API.setSlave(this.getDeviceName())
            overrideOffline = true
        }

        return API.getFirmware(overrideOffline).then(function (fwInfo) {

            let upToDate = fwInfo.version === fwInfo.latest_version
            let running = true

            let status = fwInfo.status
            if (status === API.FIRMWARE_STATUS_IDLE) {
                if (upToDate) {
                    status = FIRMWARE_STATUS_UPTODATE
                }
                else if (fwInfo.latest_version) {
                    status = FIRMWARE_STATUS_UPDATABLE
                }
                else {
                    status = FIRMWARE_STATUS_NOT_AVAILABLE
                }

                running = false
                if (this._updateRunning) {
                    this._updateRunning = false
                    this._updateFinished = true
                    Toast.show({message: gettext('Firmware has been updated.'), type: 'info', timeout: 0})
                }
            }
            else if (status === API.FIRMWARE_STATUS_ERROR) {
                running = false
                if (this._updateRunning) {
                    this._updateRunning = false
                }
            }

            let data = {
                currentVersion: fwInfo.version,
                latestVersion: fwInfo.latest_version,
                releaseDate: fwInfo.latest_date,
                url: fwInfo.latest_url,
                status: status
            }

            this.setData(data)

            return running

        }.bind(this))
    }

    pollStatus(delay) {
        return PromiseUtils.later(delay || 0).then(function () {

            return this.fetchUpdateStatus()

        }.bind(this)).catch(function (error) {

            /* Any error during polling is considered normal
             * and is treated as though the device is restarting */

            this.setData({status: API.FIRMWARE_STATUS_RESTARTING})

            return /* running = */ true

        }.bind(this)).then(function (running) {

            return PromiseUtils.later(POLLING_INTERVAL * 1000, running)

        }).then(function (running) {

            /* Stop polling once status is idle or an error occurred */
            if (!running) {
                if (!this.deviceIsSlave()) {
                    let closeButton = this.getButton('close')
                    closeButton.enable()
                }

                return
            }

            /* Carry on with polling, but don't add it to outer promise chain */
            this.pollStatus()

        }.bind(this))
    }

    getDeviceName() {
        return this._deviceName
    }

    deviceIsSlave() {
        return !Cache.isMainDevice(this.getDeviceName())
    }

    onClose() {
        if (this._updateFinished && !this.deviceIsSlave()) {
            PromiseUtils.later(1000).then(() => Window.reload())
        }
    }

}
