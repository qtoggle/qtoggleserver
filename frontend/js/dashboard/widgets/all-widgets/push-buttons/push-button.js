
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields.js'
import {UpDownField}     from '$qui/forms/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'
import * as Window       from '$qui/window.js'

import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import {DEFAULT_COLOR}  from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


/**
 * @class QToggle.DashboardSection.Widgets.PushButton.ConfigForm
 * @extends qtoggle.dashboard.widgets.WidgetConfigForm
 * @param {qtoggle.dashboard.widgets.Widget} widget
 */
class ConfigForm extends WidgetConfigForm {

    constructor({...args}) {
        super({
            fields: [
                new ColorComboField({
                    name: 'color',
                    label: gettext('Color'),
                    filterEnabled: true,
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
                    name: 'pressedValue',
                    label: gettext('Pressed Value'),
                    required: true
                }),
                new NumericField({
                    name: 'releasedValue',
                    label: gettext('Released Value'),
                    required: true
                }),
                new UpDownField({
                    name: 'timeout',
                    label: gettext('Release Timeout'),
                    unit: 'ms',
                    min: 0,
                    max: 10000,
                    step: 100,
                    description: gettext('Sets the time after which the button is automatically released. ' +
                                         'Value 0 disables automatic release.')
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
        let numberFieldNames = ['pressedValue', 'releasedValue']

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
 * @alias qtoggle.dashboard.widgets.pushbuttons.PushButton
 * @extends qtoggle.dashboard.widgets.Widget
 */
class PushButton extends Widget {

    /**
     * @constructs
     */
    constructor() {
        super()

        this._color = DEFAULT_COLOR
        this._portId = ''
        this._inverted = false
        this._pressedValue = 1
        this._releasedValue = 0
        this._timeout = 1000
        this._timeoutHandle = null

        this._bezelDiv = null
        this._handleDiv = null
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.writable && port.online !== false)
    }

    makeContent(width, height) {
        let container = $('<div class="dashboard-push-button-container"></div>')

        this._bezelDiv = this._makeBezel(width, height)
        container.css('borderWidth', `${Widgets.CELL_PADDING}em`)
        container.append(this._bezelDiv)

        this._handleDiv = this._makeHandleDiv()
        this._bezelDiv.append(this._handleDiv)

        return container
    }

    _makeBezel(width, height) {
        let diameter = Math.min(width, height) - 2 * Widgets.CELL_PADDING
        let marginTop = (height > width) ? (height - width) / 2 : 0
        let bezelDiv = $('<div class="dashboard-push-button-bezel"></div>')
        bezelDiv.css({
            'width': `${diameter}em`,
            'height': `${diameter}em`,
            'margin-top': `${marginTop}em`
        })

        return bezelDiv
    }

    _makeHandleDiv() {
        let handleDiv = $('<div class="qui-base-button dashboard-push-button-handle"></div>')
        handleDiv.css({
            background: Theme.getColor(this._color),
            margin: `${this.roundEm(Widgets.BEZEL_WIDTH)}em`
        })

        let that = this

        function pointerUp() {
            Window.$body.off('pointerup pointercancel pointerleave', pointerUp)

            that.vibrate()
            that.handleRelease()

            if (that._timeoutHandle) {
                clearTimeout(that._timeoutHandle)
                that._timeoutHandle = null
            }
        }

        handleDiv.on('pointerdown', function (e) {
            Window.$body.on('pointerup pointercancel pointerleave', pointerUp)

            that.vibrate()
            that.handlePress()

            if (that._timeout) {
                that._timeoutHandle = setTimeout(function () {
                    that._timeoutHandle = null
                    pointerUp()
                }, that._timeout)
            }

            e.preventDefault()
        })

        return handleDiv
    }

    _isBoolean() {
        let isBoolean = true
        let port = this.getPort(this._portId)
        if (port && port.type === 'number') {
            isBoolean = false
        }

        return isBoolean
    }

    handlePress() {
        if (this._isBoolean()) {
            this.setPortValue(this._portId, !this._inverted)
        }
        else {
            this.setPortValue(this._portId, this._pressedValue)
        }
    }

    handleRelease() {
        if (this._isBoolean()) {
            this.setPortValue(this._portId, this._inverted)
        }
        else {
            this.setPortValue(this._portId, this._releasedValue)
        }
    }

    configToJSON() {
        return {
            color: this._color,
            portId: this._portId,
            inverted: this._inverted,
            pressedValue: this._pressedValue,
            releasedValue: this._releasedValue,
            timeout: this._timeout
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
        if (json.pressedValue != null) {
            this._pressedValue = json.pressedValue
        }
        if (json.releasedValue != null) {
            this._releasedValue = json.releasedValue
        }
        if (json.timeout != null) {
            this._timeout = json.timeout
        }
    }

}

// TODO es7 class fields
PushButton.category = gettext('Push Buttons')
PushButton.displayName = gettext('Push Button')
PushButton.typeName = 'PushButton'
PushButton.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
PushButton.ConfigForm = ConfigForm
PushButton.vResizable = true
PushButton.hResizable = true


Widgets.register(PushButton)


export default PushButton
