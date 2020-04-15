
import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields.js'
import {ComboField}      from '$qui/forms/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields.js'
import {PasswordField}   from '$qui/forms/common-fields.js'
import {TextField}       from '$qui/forms/common-fields.js'
import {PageForm}        from '$qui/forms/common-forms.js'
import FormButton        from '$qui/forms/form-button.js'
import {ValidationError} from '$qui/forms/forms.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import URL               from '$qui/utils/url.js'

import * as BaseAPI        from '$app/api/base.js'
import * as MasterSlaveAPI from '$app/api/master-slave.js'

import * as Devices from './devices.js'


const VALID_HOST_REGEX = new RegExp('[-a-z0-9_.]{2,256}', 'i')

const logger = Devices.logger


/**
 * @alias qtoggle.devices.AddDeviceForm
 * @extends qui.forms.PageForm
 */
class AddDeviceForm extends PageForm {

    /**
     * @constructs
     */
    constructor() {
        super({
            icon: Devices.DEVICE_ICON,
            title: gettext('Add Device...'),
            pathId: 'add',
            continuousValidation: true,

            fields: [
                new TextField({
                    name: 'url',
                    label: gettext('URL'),
                    required: true,
                    placeholder: 'http://192.168.1.123/device',
                    initialValue: 'http://',

                    validate(url) {
                        if (!url.match(URL.VALID_REGEX)) {
                            throw new ValidationError(gettext('Enter a valid URL.'))
                        }
                    }
                }),
                new PasswordField({
                    name: 'password',
                    label: gettext('Password'),
                    autocomplete: false
                }),
                new ComboField({
                    name: 'poll_interval',
                    label: gettext('Polling Interval'),
                    choices: Devices.POLL_CHOICES,
                    unit: gettext('seconds')
                }),
                new CheckField({
                    name: 'listen_enabled',
                    label: gettext('Enable Listening')
                })
            ],
            data: {
                poll_interval: 0,
                listen_enabled: true
            },
            buttons: [
                new FormButton({id: 'cancel', caption: gettext('Cancel'), cancel: true}),
                new FormButton({id: 'add', caption: gettext('Add'), def: true})
            ]
        })
    }

    applyData(data) {
        logger.debug(`adding device at url ${data.url}`)

        let url = URL.parse(data.url)
        let scheme = url.scheme
        let host = url.host
        let port = url.port || (url.scheme === 'https' ? 443 : 80)
        let path = url.path || '/'
        let password = data.password || url.password

        if (url.queryStr) {
            path += `?${url.queryStr}`
        }

        return MasterSlaveAPI.postSlaveDevices(
            scheme,
            host,
            port,
            path,
            password,
            data.poll_interval,
            data.listen_enabled
        ).then(function (response) {

            logger.debug(`device "${response.name}" at url ${data.url} successfully added`)

        }).catch(function (error) {

            /* Retry with /api path, which should be a default location for qToggleServer implementations */
            if (error instanceof BaseAPI.APIError && error.messageCode === 'no such function' && url.path === '/') {

                logger.debug('retrying with /api suffix')
                url.path = '/api'
                data.url = url.toString()

                return this.applyData(data)
            }

            logger.errorStack(`failed to add device at url ${data.url}`, error)

            throw error

        }.bind(this))
    }

}


export default AddDeviceForm
