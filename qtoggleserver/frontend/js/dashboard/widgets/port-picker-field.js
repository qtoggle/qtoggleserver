
import $ from '$qui/lib/jquery.module.js'

import {gettext}        from '$qui/base/i18n.js'
import Config           from '$qui/config.js'
import {ComboField}     from '$qui/forms/common-fields/common-fields.js'
import * as Navigation  from '$qui/navigation.js'
import * as ArrayUtils  from '$qui/utils/array.js'
import * as StringUtils from '$qui/utils/string.js'

import * as Cache from '$app/cache.js'


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

            /* This will rebuild the choices list, applying the filter */
            this._widgetCall({choices: []})
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

    _filter(port) {
        /* By default, filter out internal ports */
        return !port.internal
    }

    makeChoices() {
        let ports = Object.values(Cache.getPorts())

        /* Apply implicit filtering */
        ports = ports.filter(this._filter)

        /* Apply custom filtering; bind filtering function as it's usually provided as standalone anonymous function */
        ports = ports.filter(this.filter.bind(this))

        let choices = ports.map(function (port) {
            return {
                label: this.makeLabel(port),
                matchPhrase: this.makeMatchPhrase(port),
                value: port.id,
                port: port
            }
        }, this)

        /* Only use port id to sort entries, since it already contains device name and other grouping prefixes */
        choices = ArrayUtils.sortKey(choices, c => c.port.id)

        return choices
    }

    /**
     * Build the text a search filter is matched against. The parts of the port id appear in the order in which they
     * are displayed, each one as it is displayed and, when that is a display name, followed by the corresponding id
     * part, so that a filter can span them and either name can be searched for.
     * @param {Object} port
     * @returns {String}
     */
    makeMatchPhrase(port) {
        let device = Cache.findPortSlaveDevice(port.id)
        let mainDevice = Cache.getMainDevice()

        let parts = port.id.split('.')
        if (parts.length === 1 && Config.slavesEnabled) {
            parts.splice(0, 0, mainDevice.display_name || mainDevice.name)
        }

        let phraseParts = []
        parts.forEach(function (part, i) {

            let displayName = null
            if (i === 0 && device && device.attrs['display_name']) {
                displayName = device.attrs['display_name']
            }
            else if (i === parts.length - 1 && port.display_name) {
                displayName = port.display_name
            }

            if (displayName) {
                phraseParts.push(displayName)
            }
            if (displayName !== part) {
                phraseParts.push(part)
            }

        })

        return phraseParts.join(' ').toLowerCase()
    }

    filterFunc(choice, searchText) {
        return StringUtils.intelliSearch(choice.matchPhrase, searchText) != null
    }

    makeLabelHTML() {
        /* Override label HTML method to add currently selected port anchor */

        let html = super.makeLabelHTML()

        html.css('grid-template-columns', '1fr fit-content(75%)')
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

        let port = Cache.getPort(portId)
        if (port) {
            let displayName = port.display_name || port.id
            let path = Cache.getPortPath(portId)

            return Navigation.makeInternalAnchor(path, displayName)
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
