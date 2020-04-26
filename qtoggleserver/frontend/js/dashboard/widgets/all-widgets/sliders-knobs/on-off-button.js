
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


const TEXT_FACTOR = 0.3 /* Fraction of button thickness */


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
 * @alias qtoggle.dashboard.widgets.slidersknobs.OnOffButton
 * @extends qtoggle.dashboard.widgets.Widget
 */
class OnOffButton extends Widget {

    /**
     * @constructs
     */
    constructor() {
        super()

        this._on = false
        this._color = DEFAULT_COLOR
        this._portId = ''
        this._inverted = false
        this._offValue = 0
        this._onValue = 1

        this._containerDiv = null
        this._backgroundDiv = null
        this._handleDiv = null
        this._thickness = 0
        this._vert = false
        this._dragPastThresh = false
        this._dragDelta = 0
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.writable && port.online !== false)
    }

    showCurrentValue() {
        let value = this.getPortValue(this._portId)
        if (value == null) {
            return
        }

        this._showValue(value)
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId || value == null) {
            return
        }

        this._showValue(value)
    }

    _showValue(value) {
        if (this._isBoolean()) {
            value = this._inverted ? !value : value

            if (value && !this._on) {
                this._showOn()
            }
            else if (!value && this._on) {
                this._showOff()
            }
        }
        else { /* Number */
            if (value === this._onValue && !this._on) {
                this._showOn()
            }
            else if (value === this._offValue && this._on) {
                this._showOff()
            }
        }
    }

    makeContent(width, height) {
        if (width > height) {
            this._vert = false
            this._containerDiv = this._makeHorizContent(width, height)
            this._containerDiv.removeClass('vert')
        }
        else {
            this._vert = true
            this._containerDiv = this._makeVertContent(width, height)
            this._containerDiv.addClass('vert')
        }

        /* Update the current state */
        if (this._on) {
            this._showOn()
        }
        else {
            this._showOff()
        }

        return this._containerDiv
    }

    _makeHorizContent(containerWidth, containerHeight) {
        let left = (containerWidth - 2 * containerHeight) / 2
        let top = 0
        let width = 2 * containerHeight
        let height = containerHeight

        if (containerWidth < 2 * containerHeight) {
            left = 0
            top = (containerHeight - containerWidth / 2) / 2
            width = containerWidth
            height = containerWidth / 2
        }

        let containerDiv = $('<div></div>', {class: 'dashboard-on-off-button-container'})
        containerDiv.css({
            top: `${top}em`,
            left: `${left}em`,
            width: `${width}em`,
            height: `${height}em`,
            borderWidth: `${Widgets.CELL_PADDING}em`
        })

        this._thickness = height
        this._backgroundDiv = this._makeBackground(this._thickness)
        containerDiv.append(this._backgroundDiv)

        return containerDiv
    }

    _makeVertContent(containerWidth, containerHeight) {
        let left = 0
        let top = (containerHeight - 2 * containerWidth) / 2
        let width = containerWidth
        let height = 2 * containerWidth

        if (containerHeight < 2 * containerWidth) {
            left = (containerWidth - containerHeight / 2) / 2
            top = 0
            height = containerHeight
            width = containerHeight / 2
        }

        let containerDiv = $('<div></div>', {class: 'dashboard-on-off-button-container'})
        containerDiv.css({
            top: `${top}em`,
            left: `${left}em`,
            width: `${width}em`,
            height: `${height}em`,
            borderWidth: `${Widgets.CELL_PADDING}em`
        })

        this._thickness = width
        this._backgroundDiv = this._makeBackground(this._thickness)
        containerDiv.append(this._backgroundDiv)

        return containerDiv
    }

    _makeBackground(thickness) {
        let backgroundDiv = $('<div></div>', {class: 'dashboard-on-off-button-background'})

        backgroundDiv.css('border-radius', `${Math.min(this.getContentWidth(), this.getContentHeight())}em`)

        this._handleDiv = this._makeHandle(thickness)
        backgroundDiv.append(this._handleDiv)

        this.setDragElement(backgroundDiv, this._vert ? 'y' : 'x')

        backgroundDiv.on('pointerup', function () {
            if (this._dragDelta < this._thickness * 0.05) {
                this._doSwitch()
            }
        }.bind(this))

        return backgroundDiv
    }

    _makeHandle(thickness) {
        let handleDiv = $('<div></div>', {class: 'dashboard-on-off-button-handle'})
        let bezelWidth = this.roundEm(Widgets.BEZEL_WIDTH)

        let radius = (thickness - 2 * (Widgets.CELL_PADDING + bezelWidth))
        handleDiv.css({
            width: `${radius}em`,
            height: `${radius}em`,
            margin: `${bezelWidth}em`,
            color: Theme.getColor(this._color)
        })

        let onText = $('<div></div>', {class: 'dashboard-on-off-button-text-on'})
        onText.text('ON')
        onText.css('font-size', `${TEXT_FACTOR * thickness}em`)

        let offText = $('<div></div>', {class: 'dashboard-on-off-button-text-off'})
        offText.text('OFF')
        offText.css('font-size', `${TEXT_FACTOR * thickness}em`)

        handleDiv.append(onText)
        handleDiv.append(offText)

        return handleDiv
    }

    _showOn() {
        this._on = true
        this._containerDiv.addClass('on')
        if (this._vert) {
            this._handleDiv.css({top: `${this._thickness}em`, left: 0})
        }
        else {
            this._handleDiv.css({left: `${this._thickness}em`, top: 0})
        }

        this._handleDiv.css('background', Theme.getColor(this._color))
    }

    _showOff() {
        this._on = false
        this._containerDiv.removeClass('on')
        this._handleDiv.css({left: 0, top: 0})
        this._handleDiv.css('background', '')
    }

    _doSwitch() {
        if (this._on) {
            this._showOff()
        }
        else {
            this._showOn()
        }

        /* Actually send the new state to the server */
        if (this._portId) {
            let value
            if (this._isBoolean()) {
                value = this._inverted ? !this._on : this._on
            }
            else {
                value = this._on ? this._onValue : this._offValue
            }

            this.setPortValue(this._portId, value)
        }
    }

    _isBoolean() {
        let port = this.getPort(this._portId)
        return port && port.type === 'boolean'
    }

    onDragBegin() {
        this._handleDiv.css('transition', 'none') /* Temporarily disable transitions */
        this._dragDelta = 0
    }

    onDrag(elemX, elemY, deltaX, deltaY) {
        let drag = this._vert ? deltaY : deltaX
        if (this._on) {
            drag = Math.max(-this._thickness, Math.min(0, drag)) + this._thickness
        }
        else {
            drag = Math.max(0, Math.min(this._thickness, drag))
        }

        /* Don't actually switch unless dragging is above 50% */
        let dragPastThresh = Math.abs(drag) / this._thickness > 0.5
        if (this._on) {
            dragPastThresh = !dragPastThresh
        }
        if (this._dragPastThresh !== dragPastThresh) {
            this.vibrate()
        }
        this._dragPastThresh = dragPastThresh
        this._dragDelta = Math.max(Math.abs(deltaX), Math.abs(deltaY))

        if (this._vert) {
            this._handleDiv.css({top: `${drag}em`, left: 0})
        }
        else {
            this._handleDiv.css({left: `${drag}em`, top: 0})
        }
    }

    onDragEnd(elemX, elemY, deltaX, deltaY) {
        this._handleDiv.css('transition', '') /* Restore transitions */

        let drag = this._vert ? deltaY : deltaX

        if (this._dragPastThresh) {
            if ((this._on && drag > 0) || (!this._on && drag < 0)) {
                return
            }

            this._doSwitch()
            this._dragPastThresh = false
        }
        else { /* Restore previous state, no switching */
            if (this._on) {
                this._showOn()
            }
            else {
                this._showOff()
            }
        }
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
OnOffButton.category = gettext('Sliders/Knobs')
OnOffButton.displayName = gettext('On/Off Button')
OnOffButton.typeName = 'OnOffButton'
OnOffButton.icon = new StockIcon({name: 'widget-on-off-button', stockName: 'qtoggle'})
OnOffButton.ConfigForm = ConfigForm
OnOffButton.hResizable = true
OnOffButton.vResizable = true


Widgets.register(OnOffButton)


export default OnOffButton
