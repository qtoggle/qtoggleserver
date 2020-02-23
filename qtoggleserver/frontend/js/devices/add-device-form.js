
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

import * as API from '$app/api.js'

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

                    validate(url) {
                        if (!url.match(URL.VALID_REGEX)) {
                            throw new ValidationError(gettext('Enter a valid URL.'))
                        }
                    },

                    onChange(url, form) {
                        let details = URL.parse(url)
                        let data = {}

                        data.scheme = details.scheme || 'http'
                        data.host = details.host
                        data.port = details.port || (data.scheme === 'http' ? 80 : 443)
                        data.path = details.path || '/'
                        if (details.queryStr) {
                            data.path += `?${details.queryStr}`
                        }
                        if (details.password) {
                            data.password = details.password
                        }

                        form.setData(data)
                    }
                }),
                new PasswordField({
                    name: 'password',
                    label: gettext('Password'),
                    autocomplete: false
                }),
                new TextField({
                    name: 'scheme',
                    label: gettext('Scheme'),
                    required: true,
                    separator: true,
                    placeholder: 'http',

                    validate(scheme) {
                        if (scheme !== 'http' && scheme !== 'https') {
                            throw new ValidationError(gettext('Enter a valid scheme.'))
                        }
                    }
                }),
                new TextField({
                    name: 'host',
                    label: gettext('Host'),
                    required: true,
                    placeholder: '192.168.1.123',

                    validate(host) {
                        if (!host.match(VALID_HOST_REGEX)) {
                            throw new ValidationError(gettext('Enter a valid host name.'))
                        }
                    }
                }),
                new NumericField({
                    name: 'port',
                    label: gettext('Port'),
                    min: 1,
                    max: 65535
                }),
                new TextField({
                    name: 'path',
                    label: gettext('Path'),
                    placeholder: '/'
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
                port: 80,
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

        return API.postSlaveDevices(
            data.scheme,
            data.host,
            data.port,
            data.path,
            data.password,
            data.poll_interval,
            data.listen_enabled
        ).then(function (response) {

            logger.debug(`device "${response.name}" at url ${data.url} successfully added`)

        }).catch(function (error) {

            logger.errorStack(`failed to add device at url ${data.url}`, error)

            if (error instanceof API.APIError && error.messageCode === 'no such function' && data.path === '/') {

                logger.debug('retrying with /api suffix')
                data.path = '/api'

                return this.applyData(data)
            }

            throw error

        }.bind(this))
    }

    onChange(data, fieldName) {
        let fieldNames = ['host', 'port', 'scheme', 'path']
        if (fieldNames.indexOf(fieldName) >= 0) {
            let form = this

            Promise.all(fieldNames.map(name => form.getFieldValue(name)).then(function (fieldValues) {

                let d = ObjectUtils.fromEntries(fieldNames.map((name, i) => [name, fieldValues[i]]))
                let url = new URL(d).toString()

                form.setData({url: url})

            }).catch(() => {}))
        }
    }

}


export default AddDeviceForm
