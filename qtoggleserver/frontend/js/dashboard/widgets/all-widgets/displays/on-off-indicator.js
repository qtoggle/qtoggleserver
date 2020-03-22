
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'

import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import {DEFAULT_COLOR}  from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


class ConfigForm extends WidgetConfigForm {

    constructor({...args}) {
        super({
            fields: [
                new ColorComboField({
                    name: 'color',
                    filterEnabled: true,
                    label: gettext('Color'),
                    required: true
                }),
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true,
                    onChange: (value, form) => form._showHidePortTypeFields()
                }),
                new CheckField({
                    name: 'inverted',
                    label: gettext('Inverted Logic')
                }),
                new NumericField({
                    name: 'offValue',
                    label: gettext('Off Value'),
                    required: true
                }),
                new NumericField({
                    name: 'onValue',
                    label: gettext('On Value'),
                    required: true
                })
            ],
            ...args
        })
    }

    _showHidePortTypeFields() {
        let data = this.getUnvalidatedData()
        let port = this.getPort(data.portId)
        let isBoolean = true
        if (port && port.type === 'number') {
            isBoolean = false
        }

        let booleanFieldNames = ['inverted']
        let numberFieldNames = ['offValue', 'onValue']

        if (isBoolean) {
            numberFieldNames.forEach(function (name) {
                this.getField(name).hide()
            }, this)
            booleanFieldNames.forEach(function (name) {
                this.getField(name).show()
            }, this)
        }
        else {
            booleanFieldNames.forEach(function (name) {
                this.getField(name).hide()
            }, this)
            numberFieldNames.forEach(function (name) {
                this.getField(name).show()
            }, this)
        }
    }

    onUpdateFromWidget() {
        this._showHidePortTypeFields()
    }

}


/**
 * @alias qtoggle.dashboard.widgets.displays.OnOffIndicator
 * @extends qtoggle.dashboard.widgets.Widget
 */
class OnOffIndicator extends Widget {

    /**
     * @constructs
     */
    constructor() {
        super()

        this._color = DEFAULT_COLOR
        this._portId = ''
        this._inverted = false
        this._offValue = 0
        this._onValue = 1

        this._bezelDiv = null
        this._lightDiv = null
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.online !== false)
    }

    showCurrentValue() {
        let value = this.getPortValue(this._portId)
        if (value == null) {
            return
        }

        this._showValue(value)
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId) {
            return
        }

        this._showValue(value)
    }

    _showValue(value) {
        if (this._isBoolean()) {
            value = this._inverted ? !value : value

            if (value) {
                this._showOn()
            }
            else if (!value) {
                this._showOff()
            }
        }
        else { /* Number */
            if (value === this._onValue) {
                this._showOn()
            }
            else if (value === this._offValue) {
                this._showOff()
            }
        }
    }

    makeContent(width, height) {
        let container = $('<div></div>', {class: 'dashboard-on-off-indicator-container'})

        this._bezelDiv = this._makeBezel(width, height)
        container.css('borderWidth', `${Widgets.CELL_PADDING}em`)
        container.append(this._bezelDiv)

        this._lightDiv = this._makeLightDiv()
        this._bezelDiv.append(this._lightDiv)

        return container
    }

    _makeBezel(width, height) {
        let diameter = Math.min(width, height) / 2
        let marginTop = diameter / 6
        let bezelDiv = $('<div></div>', {class: 'dashboard-on-off-indicator-bezel'})
        bezelDiv.css({
            'width': `${diameter}em`,
            'height': `${diameter}em`,
            'margin-top': `${marginTop}em`
        })

        return bezelDiv
    }

    _makeLightDiv() {
        let lightDiv = $('<div></div>', {class: 'dashboard-on-off-indicator-light'})
        lightDiv.css({
            background: Theme.getColor(this._color),
            margin: `${this.roundEm(Widgets.BEZEL_WIDTH)}em`
        })

        return lightDiv
    }

    _showOn() {
        this.getContentElement().addClass('on')
        this._lightDiv.css('background', Theme.getColor(this._color))
    }

    _showOff() {
        this.getContentElement().removeClass('on')
        this._lightDiv.css('background', '')
    }

    _isBoolean() {
        let port = this.getPort(this._portId)
        return port && port.type === 'boolean'
    }

    configToJSON() {
        return {
            color: this._color,
            portId: this._portId,
            inverted: this._inverted,
            offValue: this._offValue,
            onValue: this._onValue
        }
    }

    configFromJSON(json) {
        if (json.color) {
            this._color = json.color
        }
        if (json.portId) {
            this._portId = json.portId
        }
        if (json.inverted != null) {
            this._inverted = json.inverted
        }
        if (json.offValue != null) {
            this._offValue = json.offValue
        }
        if (json.onValue != null) {
            this._onValue = json.onValue
        }
    }

}

// TODO es7 class fields
OnOffIndicator.category = gettext('Displays')
OnOffIndicator.displayName = gettext('On/Off Indicator')
OnOffIndicator.typeName = 'OnOffIndicator'
OnOffIndicator.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
OnOffIndicator.ConfigForm = ConfigForm
OnOffIndicator.vResizable = true
OnOffIndicator.hResizable = true


Widgets.register(OnOffIndicator)


export default OnOffIndicator
