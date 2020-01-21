
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {ColorComboField} from '$qui/forms/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'

import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import {DEFAULT_COLOR}  from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'


class ConfigForm extends WidgetConfigForm {

    constructor(widget) {
        super(widget, {
            fields: [
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true
                }),
                new NumericField({
                    name: 'min',
                    label: gettext('Min Value'),
                    required: true
                }),
                new NumericField({
                    name: 'max',
                    label: gettext('Max Value'),
                    required: true
                }),
                new NumericField({
                    name: 'increment',
                    label: gettext('Increment'),
                    required: true
                }),
                new ColorComboField({
                    name: 'decColor',
                    label: gettext('Decrease Color'),
                    filterEnabled: true,
                    required: true
                }),
                new ColorComboField({
                    name: 'incColor',
                    label: gettext('Increase Color'),
                    filterEnabled: true,
                    required: true
                })
            ]
        })
    }

    fromPort(port, fieldName) {
        let data = super.fromPort(port,fieldName)

        data.unit = port.unit
        data.min = port.min != null ? port.min : 0
        data.max = port.max != null ? port.max : 100

        return data
    }

}


export default class IncDecButtons extends Widget {

    constructor() {
        super()

        this._portId = ''
        this._min = 0
        this._max = 100
        this._increment = 1
        this._decColor = DEFAULT_COLOR
        this._incColor = DEFAULT_COLOR
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.writable && port.online !== false && port.type === 'number')
    }

    makeContent(width, height) {
        let vert = width <= height

        let container = $('<div class="dashboard-inc-dec-buttons-container"></div>')
        container.css('borderWidth', `${Widgets.CELL_PADDING}em`)

        let bezelDiv = this._makeBezel(width, height, vert)
        container.append(bezelDiv)

        return container
    }

    _makeBezel(width, height, vert) {
        width -= 2 * Widgets.CELL_PADDING
        height -= 2 * Widgets.CELL_PADDING
        let bezelDiv = $('<div class="dashboard-inc-dec-buttons-bezel"></div>')
        bezelDiv.css({
            'width': `${width}em`,
            'height': `${height}em`,
            /* Setting border-radius this way (instead of percent) prevents ellipse effect */
            'border-radius': `${Math.max(width, height)}em`
        })

        let [decHandleDiv, incHandleDiv] = this._makeHandleDivs(width, height, vert)
        bezelDiv.append(decHandleDiv)
        bezelDiv.append(incHandleDiv)

        return bezelDiv
    }

    _makeHandleDivs(width, height, vert) {
        let decHandleDiv = $('<div class="qui-base-button dashboard-inc-dec-buttons-handle dec-handle"></div>')
        let incHandleDiv = $('<div class="qui-base-button dashboard-inc-dec-buttons-handle inc-handle"></div>')
        let handleDivs = decHandleDiv.add(incHandleDiv)
        let borderRadius = Math.max(width, height)

        handleDivs.css({
            'margin': `${this.roundEm(Widgets.BEZEL_WIDTH)}em`,
            'border-radius': `${borderRadius}em`
        })

        decHandleDiv.css('background', Theme.getColor(this._decColor))
        incHandleDiv.css('background', Theme.getColor(this._incColor))

        if (vert) {
            let halfHeight = this.roundEm(height / 2 - 1.5 * Widgets.BEZEL_WIDTH)
            decHandleDiv.css({
                'border-bottom-left-radius': 0,
                'border-bottom-right-radius': 0,
                'margin-bottom': 0,
                'bottom': 'auto',
                'height': `${halfHeight}em`
            })
            incHandleDiv.css({
                'border-top-left-radius': 0,
                'border-top-right-radius': 0,
                'margin-top': 0,
                'top': 'auto',
                'height': `${halfHeight}em`
            })
        }
        else {
            let halfWidth = this.roundEm(width / 2 - 1.5 * Widgets.BEZEL_WIDTH)
            decHandleDiv.css({
                'border-top-right-radius': 0,
                'border-bottom-right-radius': 0,
                'margin-right': 0,
                'right': 'auto',
                'width': `${halfWidth}em`
            })
            incHandleDiv.css({
                'border-top-left-radius': 0,
                'border-bottom-left-radius': 0,
                'margin-left': 0,
                'left': 'auto',
                'width': `${halfWidth}em`
            })
        }

        /* Plus/minus signs */

        decHandleDiv.append(this._makeHandleSign('&minus;'))
        incHandleDiv.append(this._makeHandleSign('&plus;'))

        decHandleDiv.on('click', this.handleDec.bind(this))
        incHandleDiv.on('click', this.handleInc.bind(this))

        return [decHandleDiv, incHandleDiv]
    }

    _makeHandleSign(sign) {
        let signSpan = $('<span class="dashboard-inc-dec-buttons-handle-sign"></span>')
        signSpan.html(sign)

        return signSpan
    }

    handleDec() {
        let value = this.getPortValue(this._portId)
        if (value - this._increment >= this._min) {
            value -= this._increment
        }

        this.setPortValue(this._portId, value)
    }

    handleInc() {
        let value = this.getPortValue(this._portId)
        if (value + this._increment <= this._max) {
            value += this._increment
        }

        this.setPortValue(this._portId, value)
    }

    configToJSON() {
        return {
            portId: this._portId,
            min: this._min,
            max: this._max,
            increment: this._increment,
            decColor: this._decColor,
            incColor: this._incColor
        }
    }

    configFromJSON(json) {
        if (json.portId) {
            this._portId = json.portId
        }
        if (json.min != null) {
            this._min = json.min
        }
        if (json.max != null) {
            this._max = json.max
        }
        if (json.increment != null) {
            this._increment = json.increment
        }
        if (json.decColor != null) {
            this._decColor = json.decColor
        }
        if (json.incColor != null) {
            this._incColor = json.incColor
        }
    }

}

// TODO es7 class fields
IncDecButtons.category = gettext('Push Buttons')
IncDecButtons.displayName = gettext('Increase/Decrease Button')
IncDecButtons.typeName = 'IncDecButtons'
IncDecButtons.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
IncDecButtons.ConfigForm = ConfigForm
IncDecButtons.vResizable = true
IncDecButtons.hResizable = true


Widgets.register(IncDecButtons)
