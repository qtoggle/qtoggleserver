/**
 * @namespace qtoggle.common.backuprestore
 */


import Logger from '$qui/lib/logger.module.js'

import {gettext}           from '$qui/base/i18n.js'
import * as ObjectUtils    from '$qui/utils/object.js'
import * as PromiseUtils   from '$qui/utils/promise.js'
import * as StringUtils    from '$qui/utils/string.js'

import * as API from '$app/api.js'


const logger = Logger.get('qtoggle.common.backuprestore')


/**
 * A backup/restore elementary operation, such as updating attributes of a port.
 * @alias qtoggle.common.backuprestore.Operation
 * @private
 */
class Operation {

    constructor(logMessage, displayMessage, func, ...args) {
        this.logMessage = logMessage
        this.displayMessage = displayMessage
        this.func = func
        this.args = args
    }

    run(context) {
        logger.debug(this.logMessage)

        let args = this.args.slice()
        args.splice(0, 0, context)

        return this.func.apply(null, args)
    }

}


/**
 * Backup/restore session context.
 * @alias qtoggle.common.backuprestore.Context
 * @private
 */
class Context {

    constructor(slaveName, modalProgress, operations) {
        this.slaveName = slaveName
        this.modalProgress = modalProgress
        this.operations = operations
        this.count = 0
        this.totalCount = operations.length
    }

    prepareAPICall() {
        if (this.slaveName) {
            API.setSlave(this.slaveName)
        }
    }

    run() {
        logger.debug(`running ${this.operations.length} operations`)

        return this.runNext().then(function () {

            logger.debug('done')
            this.modalProgress.setMessage('Operation completed successfully')

            /* Display the final done message for a little while */
            return PromiseUtils.later(500)

        }.bind(this))
    }

    runNext() {
        if (this.operations.length) {
            let op = this.operations.shift()
            let progressPercent = (++this.count) * 100 / this.totalCount

            logger.debug(`operation ${this.count}/${this.totalCount}: ${op.logMessage}`)
            this.modalProgress.setMessage(op.displayMessage)
            this.modalProgress.setProgressPercent(progressPercent)

            return op.run(this).then(() => this.runNext())
        }
    }

}


function applyDefaultDeviceConfig(context, deviceAttrs) {
    let promise = Promise.resolve()

    /* Work on copy, as we'll pop some attributes */
    deviceAttrs = ObjectUtils.copy(deviceAttrs)

    /* Never update device name via default configuration */
    ObjectUtils.pop(deviceAttrs, 'name')

    /* Don't overwrite display name */
    if (context.deviceAttrs['display_name']) {
        ObjectUtils.pop(deviceAttrs, 'display_name')
    }

    /* Update device attributes */
    promise = promise.then(function () {
        context.prepareAPICall()
        return API.patchDevice(deviceAttrs)
    })

    return promise
}

function applyDefaultPortConfig(context, portAttrs) {
    let promise = Promise.resolve()
    let portId = portAttrs.id
    let portAttrdefs = portId in context.ports ? context.ports[portId].definitions : {}

    /* Work on copy, as we'll pop some attributes */
    portAttrs = ObjectUtils.copy(portAttrs)

    if (portAttrs.virtual) {
        /* Virtual ports have to be added to device */

        if (context.ports.find(p => p.id === portId)) {
            /* If port already exists on device, remove it first */
            promise = promise.then(function () {
                context.prepareAPICall()
                return API.deletePort(portId)
            })
        }

        let id = portAttrs['id']
        let type = portAttrs['type']
        let min = portAttrs['min']
        let max = portAttrs['max']
        let integer = portAttrs['integer']
        let step = portAttrs['step']
        let choices = portAttrs['choices']

        /* Actually add the port */
        promise = promise.then(function () {
            context.prepareAPICall()
            return API.postPorts(id, type, min, max, integer, step, choices)
        })
    }

    /* Pop standard non-modifiable attributes */
    ObjectUtils.forEach(API.STD_PORT_ATTRDEFS, function (name, def) {
        if (!def.modifiable) {
            ObjectUtils.pop(portAttrs, name)
        }
    })

    /* Pop additional non-modifiable attributes */
    ObjectUtils.forEach(portAttrdefs, function (name, def) {
        if (!def.modifiable) {
            ObjectUtils.pop(portAttrs, name)
        }
    })

    let portValue = ObjectUtils.pop(portAttrs, 'value')

    /* Update port attributes */
    promise = promise.then(function () {
        context.prepareAPICall()
        return API.patchPort(portId, portAttrs)
    })

    /* Set port value, if any */
    if (portValue != null) {
        promise = promise.then(function () {
            context.prepareAPICall()
            return API.patchPortValue(portId, portValue)
        })
    }

    return promise
}

function applyDefaultWebhooksConfig(context, webhooksConfig) {
    let promise = Promise.resolve()

    if (context.deviceAttrs.flags.indexOf('reverse') < 0) {
        return promise
    }

    promise = promise.then(function () {
        context.prepareAPICall()
        return API.patchWebhooks(
            webhooksConfig.enabled,
            webhooksConfig.scheme,
            webhooksConfig.host,
            webhooksConfig.port,
            webhooksConfig.path,
            webhooksConfig.timeout,
            webhooksConfig.retries
        )
    })

    return promise
}

function applyDefaultReverseConfig(context, reverseConfig) {
    let promise = Promise.resolve()

    if (context.deviceAttrs.flags.indexOf('reverse') < 0) {
        return promise
    }

    promise = promise.then(function () {
        context.prepareAPICall()
        return API.patchReverse(
            reverseConfig.enabled,
            reverseConfig.scheme,
            reverseConfig.host,
            reverseConfig.port,
            reverseConfig.path,
            reverseConfig.timeout
        )
    })

    return promise
}


/**
 * Apply default configuration to main device or to a slave device.
 * @alias qtoggle.common.backuprestore.applyDefaultConfig
 * @param {?String} slaveName slave name or `null` for main device
 * @param {Object} config backup configuration to restore
 * @param {qui.pages.commonpages.ModalProgressPage} modalProgress
 * @returns Promise
 */
export function applyDefaultConfig(slaveName, config, modalProgress) {
    let operations = []

    operations.push(
        new Operation(
            'fetching device attributes',
            gettext('Fetching device attributes'),
            function (context) {
                context.prepareAPICall()
                return API.getDevice().then(deviceAttrs => (context.deviceAttrs = deviceAttrs))
            }
        )
    )

    operations.push(
        new Operation(
            'fetching port attributes',
            gettext('Fetching port attributes'),
            function (context) {
                context.prepareAPICall()
                return API.getPorts().then(ports => (context.ports = ports))
            }
        )
    )

    if (config['device']) {
        operations.push(
            new Operation(
                'pushing device attributes',
                gettext('Pushing device attributes'),
                applyDefaultDeviceConfig,
                config['device']
            )
        )
    }

    if (config['ports']) {
        config['ports'].forEach(function (portAttrs) {
            let logMessage = `pushing port ${portAttrs['id']} attributes`
            let displayMessage = gettext('Pushing port %(port)s attributes')
            displayMessage = StringUtils.formatPercent(displayMessage, {port: portAttrs['id']})

            operations.push(new Operation(logMessage, displayMessage, applyDefaultPortConfig, portAttrs))
        })
    }

    if (config['webhooks']) {
        operations.push(
            new Operation(
                'pushing webhooks configuration',
                gettext('Pushing webhooks configuration'),
                applyDefaultWebhooksConfig,
                config['webhooks']
            )
        )
    }
    if (config['reverse']) {
        operations.push(
            new Operation(
                'pushing reverse API calls configuration',
                gettext('Pushing reverse API calls configuration'),
                applyDefaultReverseConfig,
                config['reverse']
            )
        )
    }

    logger.debug(`applying default configuration for ${slaveName || 'main device'}`)

    return new Context(slaveName, modalProgress, operations).run()
}
