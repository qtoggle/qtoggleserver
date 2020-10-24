
import Logger from '$qui/lib/logger.module.js'

import {AssertionError}  from '$qui/base/errors.js'
import {gettext}         from '$qui/base/i18n.js'
import {PageForm}        from '$qui/forms/common-forms/common-forms.js'
import FormButton        from '$qui/forms/form-button.js'
import {ErrorMapping}    from '$qui/forms/forms.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as FilesUtils   from '$qui/utils/files.js'
import * as PromiseUtils from '$qui/utils/promise.js'
import * as DateUtils    from '$qui/utils/date.js'
import * as Window       from '$qui/window.js'

import * as BaseAPI         from '$app/api/base.js'
import * as ProvisioningAPI from '$app/api/provisioning.js'
import * as Cache           from '$app/cache.js'

import OperationCheckField from './operation-check-field.js'


const logger = Logger.get('qtoggle.common.backup')


/**
 * Device backup form.
 * @alias qtoggle.common.BackupForm
 * @extends qui.forms.commonforms.PageForm
 */
class BackupForm extends PageForm {

    /**
     * @constructs
     * @param {String} deviceName
     */
    constructor(deviceName) {
        super({
            icon: new StockIcon({name: 'upload'}),
            title: gettext('Backup Configuration'),
            pathId: 'backup',
            compact: true,
            autoDisableDefaultButton: false,
            modal: !Window.isSmallScreen(),

            buttons: [
                new FormButton({id: 'cancel', caption: gettext('Cancel'), cancel: true}),
                new FormButton({id: 'create', caption: gettext('Create'), def: true})
            ]
        })

        this._deviceName = deviceName
        this._backupEndpoints = []
        this._running = false
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
     * @param {qtoggle.api.provisioning.BackupEndpoint} endpoint
     */
    addBackupEndpoint(endpoint) {
        let field = new OperationCheckField({
            name: endpoint.getName(),
            label: endpoint.displayName,
            initialValue: true
        })

        this.addField(-1, field)
        this._backupEndpoints.push(endpoint)
    }

    /**
     * @returns {String}
     */
    getDeviceName() {
        return this._deviceName
    }

    /**
     * @returns {Boolean}
     */
    deviceIsSlave() {
        return !Cache.isMainDevice(this.getDeviceName())
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
     * @returns {Promise}
     */
    performBackupOnEndpoint(endpoint) {
        logger.debug(`requesting backup data on ${endpoint.path}`)

        let checkField = this.getField(endpoint.getName())
        checkField.setProgress(-1)

        return PromiseUtils.later(500).then(function () {

            if (this.deviceIsSlave()) {
                BaseAPI.setSlaveName(this.getDeviceName())
            }

            return BaseAPI.apiCall({method: endpoint.backupMethod, path: endpoint.path})

        }.bind(this)).then(function (result) {

            result = endpoint.prepareBackupData(result)

            checkField.setApplied()
            return result

        }).catch(function (error) {

            logger.errorStack(`backup data request failed on ${endpoint.path}`, error)
            throw new ErrorMapping({[endpoint.getName()]: error})

        })
    }

    cancelBackup() {
        if (this._running) {
            logger.debug('cancelling backup')
            this._running = false
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    applyData(data) {
        let endpoints = this._backupEndpoints.filter(e => data[e.getName()])
        let promise = Promise.resolve()
        let backupData = {}

        endpoints.forEach(function (endpoint) {
            promise = promise.then(function () {
                if (!this._running) {
                    return
                }
                return this.performBackupOnEndpoint(endpoint).then(function (result) {
                    backupData[endpoint.getName()] = result
                })
            }.bind(this))
        }.bind(this))

        promise.then(function () {

            let content = JSON.stringify(backupData, /* replacer = */ null, /* space = */ 4)
            let dateStr = DateUtils.formatPercent(new Date(), '%Y-%m-%d')
            let filename = `backup-${this.getDeviceName()}-${dateStr}.json`

            FilesUtils.clientSideDownload(filename, 'application/json', content)

        }.bind(this)).catch(function () {

            /* Mark all remaining endpoints as skipped, in case of error */
            this.getEndpointCheckFields().forEach(function (field) {
                if (!field.isApplied() && !field.hasError() && field.getValue()) {
                    field.setWarning(gettext('Backup has been skipped.'))
                }
            })

        }.bind(this)).then(function () {

            this._running = false
            logger.debug('backup ended')

        }.bind(this))

        logger.debug('starting backup')
        this._running = true

        return promise
    }

    onClose() {
        this.cancelBackup()
    }

    showProgress(progress) {
        /* Disable default button */
        this.getButton('create').disable()

        /* Disable all endpoint check fields */
        this.getEndpointCheckFields().forEach(f => f.disable())
    }

    hideProgress() {
        /* Enable default button */
        this.getButton('create').enable()

        /* Enable all endpoint check fields */
        this.getEndpointCheckFields().forEach(f => f.enable())
    }

}


export default BackupForm
