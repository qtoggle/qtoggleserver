
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'

import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'


/**
 * @class QToggle.DashboardSection.Widgets.OnOffIndicator.ConfigForm
 * @extends QToggle.DashboardSection.Widgets.WidgetConfigForm
 * @param {QToggle.DashboardSection.Widgets.Widget} widget
 */
class ConfigForm extends WidgetConfigForm {

    constructor(widget) {
        super(widget, {
            fields: [
                new ColorComboField({
                    name: 'color',
                    label: gettext('Color'),
                    required: true
                }),
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true,
                    filter: port => port.enabled && port.writable
                }),
                new CheckField({
                    name: 'inverted',
                    label: gettext('Inverted Logic')
                })
            ]
        })
    }

}


/**
 * @class QToggle.DashboardSection.Widgets.OnOffIndicator
 * @extends QToggle.DashboardSection.Widgets.Widget
 */
export default class OnOffIndicator extends Widget {

    constructor() {
        super()

        this._color = '@interactive-color'
        this._portId = ''
        this._inverted = false

        this._bezelDiv = null
        this._lightDiv = null
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.writable && port.online !== false && port.type === 'boolean')
    }

    showCurrentValue() {
        let value = this.getPortValue(this._portId)
        if (value == null) {
            return
        }

        if (this._inverted ? !value : value) {
            this._showOn()
        }
        else {
            this._showOff()
        }
    }

    makeContent(width, height) {
        let container = $('<div class="dashboard-on-off-indicator-container"></div>')

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
        let bezelDiv = $('<div class="dashboard-on-off-indicator-bezel"></div>')
        bezelDiv.css({
            'width': `${diameter}em`,
            'height': `${diameter}em`,
            'margin-top': `${marginTop}em`
        })

        return bezelDiv
    }

    _makeLightDiv() {
        let lightDiv = $('<div class="dashboard-on-off-indicator-light"></div>')
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

    configToJSON() {
        return {
            color: this._color,
            portId: this._portId,
            inverted: this._inverted
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
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId) {
            return
        }

        value = this._inverted ? !value : value

        if (value) {
            this._showOn()
        }
        else {
            this._showOff()
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
