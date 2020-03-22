
import $ from '$qui/lib/jquery.module.js'

import {gettext}       from '$qui/base/i18n.js'
import Config          from '$qui/config.js'
import {ComboField}    from '$qui/forms/common-fields.js'
import * as Navigation from '$qui/navigation.js'
import * as ArrayUtils from '$qui/utils/array.js'

import * as Cache from '$app/cache.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


/**
 * @alias qtoggle.dashboard.widgets.PortPickerField
 * @extends qui.forms.commonfields.ComboField
 */
class PortPickerField extends ComboField {

    /**
     * @constructs
     * @param {...*} args
     * @param {Function} [filter]
     */
    constructor({filter = null, ...args}) {
        super({filterEnabled: true, ...args})

        if (filter) {
            this.filter = filter
        }

        this._currentAnchorElement = null
    }

    /**
     * @param {Object} port
     * @returns {Boolean}
     */
    filter(port) {
        return true
    }

    makeChoices() {
        let choices = Object.values(Cache.getPorts()).filter(this.filter.bind(this)).map(function (port) {

            return {
                label: this.makeLabel(port),
                value: port.id
            }

        }, this)

        return ArrayUtils.sortKey(choices, choice => choice.value)
    }

    makeLabelHTML() {
        let html = super.makeLabelHTML()

        html.append(this.makeCurrentHMTL())

        return html
    }

    /**
     * @returns {jQuery}
     */
    makeCurrentHMTL() {
        let currentDiv = $('<div></div>', {class: 'port-picker-current'})

        this._currentAnchorElement = this.makeCurrentAnchor()
        currentDiv.append(this._currentAnchorElement)

        return currentDiv
    }

    /**
     * @param {?String} portId
     * @returns {jQuery}
     */
    makeCurrentAnchor(portId = null) {
        if (portId == null) {
            return $('<span></span>').text(gettext('none'))
        }

        let displayName = portId
        let port = Cache.getPort(portId)
        if (port) {
            displayName = port.display_name || port.id
            return Navigation.makeInternalAnchor(`/ports/${portId}`, displayName)
        }
        else {
            return $('<span></span>').text(portId)
        }
    }

    updateCurrentAnchor(portId) {
        let newElement = this.makeCurrentAnchor(portId)
        this._currentAnchorElement.replaceWith(newElement)
        this._currentAnchorElement = newElement
    }

    setValue(value) {
        super.setValue(value)
        this.updateCurrentAnchor(value)
    }

    handleChange(value) {
        super.handleChange(value)
        this.updateCurrentAnchor(value)
    }

    /**
     * @param {Object} port
     * @returns {jQuery}
     */
    makeLabel(port) {
        let portId = port.id
        let device = Cache.findPortSlaveDevice(portId)
        let mainDevice = Cache.getMainDevice()

        let parts = port.id.split('.')
        if (parts.length === 1 && Config.slavesEnabled) {
            parts.splice(0, 0, mainDevice.display_name || mainDevice.name)
        }

        let labelDiv = $('<div></div>', {class: 'port-picker-combo-item'})

        parts.forEach(function (part, i) {

            let line = $('<div></div>', {class: 'port-picker-combo-item-line'})
            if (i < parts.length - 1) {
                line.addClass('device')
            }
            else {
                line.addClass('port')
            }

            if (i === 0 && device && device.attrs.display_name) {
                part = device.attrs.display_name
            }
            else if (i === parts.length - 1 && port.display_name) {
                part = port.display_name
            }

            line.append(` ${part}`)
            line.css('padding-left', `${(i * 0.9)}em`)

            labelDiv.append(line)
        })

        if (labelDiv.children('div').length === 1) {
            labelDiv.addClass('single-line')
        }

        return labelDiv
    }

}


export default PortPickerField
