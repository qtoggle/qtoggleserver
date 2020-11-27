
import Logger from '$qui/lib/logger.module.js'

import {AssertionError}  from '$qui/base/errors.js'
import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {FilePickerField} from '$qui/forms/common-fields/common-fields.js'
import {PageForm}        from '$qui/forms/common-forms/common-forms.js'
import FormButton        from '$qui/forms/form-button.js'
import {ErrorMapping}    from '$qui/forms/forms.js'
import {ValidationError} from '$qui/forms/forms.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Toast        from '$qui/messages/toast.js'
import * as PromiseUtils from '$qui/utils/promise.js'
import * as StringUtils  from '$qui/utils/string.js'
import URL               from '$qui/utils/url.js'
import * as Window       from '$qui/window.js'

import * as BaseAPI         from '$app/api/base.js'
import * as ProvisioningAPI from '$app/api/provisioning.js'
import * as Cache           from '$app/cache.js'

import OperationCheckField from './operation-check-field.js'


const INVALID_BACKUP_FILE_MESSAGE = gettext('Please supply a valid backup file!')
const RESTORE_API_CALL_TIMEOUT = 120000

const logger = Logger.get('qtoggle.common.restore')


/**
 * Device restore form.
 * @alias qtoggle.common.RestoreForm
 * @extends qui.forms.commonforms.PageForm
 */
class RestoreForm extends PageForm {

    /**
     * @constructs
     * @param {String} deviceName
     */
    constructor(deviceName) {
        super({
            icon: new StockIcon({name: 'download'}),
            title: gettext('Restore Configuration'),
            pathId: 'restore',
            compact: true,
            autoDisableDefaultButton: false,
            modal: !Window.isSmallScreen(),

            fields: [
                new FilePickerField({
                    name: 'backup_file',
                    label: gettext('Backup File'),
                    accept: ['application/json'],
                    forceOneLine: true,
                    onChange(value, form) {
                        /* value is a File[] array */
                        form.handleFileSelected(value[0])
                    }
                }),
                new CheckField({
                    name: 'reboot_after',
                    label: gettext('Reboot Device'),
                    initialValue: true,
                    separator: true
                })
            ],
            buttons: [
                new FormButton({id: 'cancel', caption: gettext('Cancel'), cancel: true}),
                new FormButton({id: 'restore', caption: gettext('Restore'), def: true})
            ]
        })

        this._deviceName = deviceName
        this._newDeviceName = null
        this._backupEndpoints = []
        this._running = false
        this._content = null
        this._suppliedNames = null

        this.getButton('restore').disable()
    }

    load() {
        let deviceAttrs = this.getDeviceAttrs()
        let flags = deviceAttrs['flags']

        if (this.deviceIsSlave()) {
            BaseAPI.setSlaveName(this.getDeviceName())
        }

        return ProvisioningAPI.getBackupEndpoints(flags).then(function (endpoints) {

            endpoints.forEach(e => this.addBackupEndpoint(e))

        }.bind(this)).catch(function (error) {

            logger.error(`failed to get backup endpoints: ${error}`)
            this.setError(gettext('Failed to obtain backup information.'))

        }.bind(this))
    }

    /**
     * Executed as soon as a backup file has been selected.
     * @param {?File} file
     */
    handleFileSelected(file) {
        let fields = this.getEndpointCheckFields()
        let restoreButton = this.getButton('restore')

        fields.forEach(function (f) {
            f.hide()
            f.clearApplied()
            f.clearWarning()
            f.clearError()
        })
        restoreButton.disable()
        this.clearError()
        this._content = null
        this._suppliedNames = null

        if (!file) { /* File selection cleared */
            return
        }

        file.text().then(function (content) {

            /* Parsing should succeed, given that we already passed the validation */
            try {
                content = JSON.parse(content)
            }
            catch (e) {
                this.setError(new ValidationError(INVALID_BACKUP_FILE_MESSAGE))
                return
            }

            /* Let's see what endpoints are both supplied and supported by device */
            let suppliedNames = Object.keys(content)
            let suppliedFields = fields.filter(f => suppliedNames.includes(f.getName()))
            if (!suppliedFields.length) {
                this.setError(new ValidationError(INVALID_BACKUP_FILE_MESSAGE))
                return
            }

            suppliedFields.forEach(f => f.show())
            restoreButton.enable()
            this._content = content
            this._suppliedNames = suppliedFields.map(f => f.getName())

        }.bind(this))
    }

    /**
     * @param {qtoggle.api.provisioning.BackupEndpoint} endpoint
     */
    addBackupEndpoint(endpoint) {
        let field = new OperationCheckField({
            name: endpoint.getName(),
            label: endpoint.displayName,
            initialValue: true,
            hidden: true
        })

        this.addField(this.getFields().length - 1, field)
        this._backupEndpoints.push(endpoint)
    }

    /**
     * @returns {String}
     */
    getDeviceName() {
        return this._newDeviceName || this._deviceName
    }

    /**
     * @returns {Boolean}
     */
    deviceIsSlave() {
        return !Cache.isMainDevice(this._deviceName) && !Cache.isMainDevice(this._newDeviceName)
    }

    /**
     * @returns {Object}
     */
    getDeviceAttrs() {
        if (this.deviceIsSlave()) {
            let device = Cache.getSlaveDevice(this.getDeviceName())
            if (!device) {
                throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
            }

            return device.attrs
        }
        else {
            return Cache.getMainDevice()
        }
    }

    /**
     * @returns {qtoggle.common.OperationCheckField[]}
     */
    getEndpointCheckFields() {
        return this._backupEndpoints.map(e => this.getField(e.getName()))
    }

    /**
     * @param {qtoggle.api.provisioning.BackupEndpoint} endpoint
     * @param {*} data
     * @returns {Promise}
     */
    performRestoreOnEndpoint(endpoint, data) {
        logger.debug(`restoring data on ${endpoint.path}`)

        let endpointData = endpoint.prepareRestoreData(data)
        let checkField = this.getField(endpoint.getName())
        checkField.setProgress(-1)

        return PromiseUtils.later(500).then(function () {

            if (this.deviceIsSlave()) {
                BaseAPI.setSlaveName(this.getDeviceName())
            }

            return BaseAPI.apiCall({
                method: endpoint.restoreMethod,
                path: endpoint.path,
                data: endpointData,
                timeout: RESTORE_API_CALL_TIMEOUT
            }).then(function () {
                if ((endpoint === ProvisioningAPI.DEVICE_BACKUP_ENDPOINT ||
                     endpoint === ProvisioningAPI.DEVICE_PATCH_BACKUP_ENDPOINT) &&
                    'name' in endpointData) {

                    /* Device has been renamed */
                    this._newDeviceName = endpointData['name']
                }
            }.bind(this))

        }.bind(this)).then(function (result) {

            checkField.setApplied()
            return result

        }).catch(function (error) {

            let deviceData = null
            let portData = null
            let extraMessage = null

            /* Attempt to find problematic device */
            if ('index' in error.params) {
                let index = error.params['index']
                deviceData = endpointData[index]
                if (deviceData) {
                    let url = new URL(deviceData).alter({password: null})
                    extraMessage = gettext('Problematic device has URL "%(url)s", at position %(position)s.')
                    extraMessage = StringUtils.formatPercent(extraMessage, {url, position: index})
                }
            }

            /* Attempt to find problematic port */
            if ('id' in error.params) {
                let id = error.params['id']
                portData = endpointData.find(d => d['id'] === id)
                if (portData) {
                    extraMessage = gettext('Problematic port has id "%(id)s".')
                    extraMessage = StringUtils.formatPercent(extraMessage, {id})
                }
            }

            if (extraMessage) {
                error.message += ' ' + extraMessage
            }

            logger.errorStack(`restore data request failed on ${endpoint.path}, `, error)
            throw new ErrorMapping({[endpoint.getName()]: error})
        })
    }

    cancelRestore() {
        if (this._running) {
            logger.debug('cancelling restore')
            this._running = false
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    applyData(data) {
        let endpoints = this._backupEndpoints.filter(e => this._suppliedNames.includes(e.getName()))
        endpoints = endpoints.filter(e => data[e.getName()])
        let promise = Promise.resolve()

        endpoints.forEach(function (endpoint) {
            promise = promise.then(function () {
                if (!this._running) {
                    return
                }

                return this.performRestoreOnEndpoint(endpoint, this._content)
            }.bind(this))
        }.bind(this))

        promise.then(function () {

            Toast.info(gettext('Configuration has been restored.'))

            /* Reboot device, but don't keep the current form open */
            if (data['reboot_after']) {
                let prevPage = this.getPrev() /* Previous page is assumed to be a device form */
                prevPage.doReboot(this.getDeviceName(), logger)
            }

        }.bind(this)).catch(function () {

            /* Mark all remaining endpoints as skipped, in case of error */
            this.getEndpointCheckFields().forEach(function (field) {
                if (!field.isApplied() && !field.hasError() && field.getValue()) {
                    field.setWarning(gettext('Restore has been skipped.'))
                }
            })

        }.bind(this)).then(function () {

            this._running = false
            logger.debug('restore ended')

        }.bind(this))

        logger.debug('starting restore')
        this._running = true

        return promise
    }

    onClose() {
        this.cancelRestore()
    }

    showProgress(progress) {
        /* Disable default button */
        this.getButton('restore').disable()

        /* Disable all endpoint check fields */
        this.getEndpointCheckFields().forEach(f => f.disable())
    }

    hideProgress() {
        /* Enable all endpoint check fields */
        this.getEndpointCheckFields().forEach(f => f.enable())
    }

}


export default RestoreForm
