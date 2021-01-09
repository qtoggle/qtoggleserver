
import {gettext}         from '$qui/base/i18n.js'
import {ColorComboField} from '$qui/forms/common-fields/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import {UpDownField}     from '$qui/forms/common-fields/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'
import * as ArrayUtils   from '$qui/utils/array.js'
import * as Colors       from '$qui/utils/colors.js'
import * as ObjectUtils  from '$qui/utils/object.js'

import PortPickerField from '$app/dashboard/widgets/port-picker-field.js'
import * as Widgets    from '$app/dashboard/widgets/widgets.js'

import '$app/widgets/pie-chart.js'

import {BaseChartConfigForm} from './base-chart-widget.js'
import {BaseChartWidget}     from './base-chart-widget.js'


class ConfigForm extends BaseChartConfigForm {

    constructor({...args}) {
        super({
            fields: [
                new TextField({
                    name: 'unit',
                    label: gettext('Unit'),
                    maxLength: 16
                }),
                new NumericField({
                    name: 'multiplier',
                    label: gettext('Multiplier'),
                    description: gettext('A multiplying factor that brings the port value to the 0..100 range.'),
                    required: true
                }),
                new UpDownField({
                    name: 'numPorts',
                    label: gettext('Ports'),
                    min: 1,
                    max: 20,
                    onChange: (value, form) => form._updatePortFields()
                })
            ],
            ...args
        })
    }

    onUpdateFromWidget() {
        this._updatePortFields()
    }

    _updatePortFields() {
        let portIdFields =
                this.getFields().filter(field => field.getName().match(new RegExp('portId\\d+')))
        let portLabelFields =
                this.getFields().filter(field => field.getName().match(new RegExp('portLabel\\d+')))
        let portColorFields =
                this.getFields().filter(field => field.getName().match(new RegExp('portColor\\d+')))

        let portFields = [...portIdFields, ...portLabelFields, ...portColorFields]

        let data = this.getUnvalidatedData()
        let lastPortFieldNo = portIdFields.length - 1

        /* Add new needed fields */
        ArrayUtils.range(lastPortFieldNo + 1, data.numPorts).forEach(function (no) {

            let fields = this._addPortFields(no)

            portFields.push(fields.idField)
            portFields.push(fields.labelField)
            portFields.push(fields.colorField)

        }.bind(this))

        /* Show all used fields */
        ArrayUtils.range(0, data.numPorts).forEach(function (no) {

            let fields = this._getPortFields(no)

            fields.idField.show()
            fields.labelField.show()
            fields.colorField.show()

        }.bind(this))

        /* Hide all unused fields */
        ArrayUtils.range(data.numPorts, lastPortFieldNo + 1).forEach(function (no) {

            let fields = this._getPortFields(no)

            fields.idField.hide()
            fields.labelField.hide()
            fields.colorField.hide()

        }.bind(this))

        /* Multiplier field only makes sense when using one single port */
        /* Unit field only makes sense when using multiple ports */
        let multiplierField = this.getField('multiplier')
        let unitField = this.getField('unit')
        if (data.numPorts > 1) {
            multiplierField.hide()
            unitField.show()
        }
        else {
            multiplierField.show()
            unitField.hide()
        }

        /* Hide port1 label if only one port is used */
        let port0LabelField = this._getPortFields(0).labelField
        if (port0LabelField) {
            if (data.numPorts > 1) {
                port0LabelField.show()
            }
            else {
                port0LabelField.hide()
            }
        }
    }

    _addPortFields(no) {
        let idField = new PortPickerField({
            name: `portId${no}`,
            label: `${gettext('Port')} ${no + 1}`,
            required: true,
            separator: true,
            filter: port => port.type === 'number',
            onChange: (value, form) => form._handlePortSelect(value, no)
        })

        let labelField = new TextField({
            name: `portLabel${no}`,
            label: `${gettext('Label')} ${no + 1}`
        })

        let colorField = new ColorComboField({
            name: `portColor${no}`,
            label: `${gettext('Color')} ${no + 1}`,
            filterEnabled: true,
            required: true
        })

        this.addField(-1, idField)
        this.addField(-1, labelField)
        this.addField(-1, colorField)

        return {
            idField: idField,
            labelField: labelField,
            colorField: colorField
        }
    }

    _getPortFields(no) {
        let idField = this.getField(`portId${no}`)
        let labelField = this.getField(`portLabel${no}`)
        let colorField = this.getField(`portColor${no}`)

        return {
            idField: idField,
            labelField: labelField,
            colorField: colorField
        }
    }

    _handlePortSelect(portId, no) {
        let port = this.getPort(portId)
        if (!port) {
            return
        }

        let portFields = this._getPortFields(no)
        let labelField = portFields.labelField
        if (!labelField) {
            return
        }

        if (labelField.getValue()) {
            return
        }

        let displayName = port.display_name || port.id
        labelField.setValue(displayName)
    }

    fromWidget(widget) {
        let data = super.fromWidget(widget)

        data.numPorts = data.portIds.length
        ArrayUtils.range(0, data.numPorts).forEach(function (i) {
            data[`portId${i}`] = data.portIds[i]
            data[`portLabel${i}`] = data.labels[i]
            data[`portColor${i}`] = data.colors[i]
        })

        return data
    }

    toWidget(data, widget) {
        data.portIds = []
        data.labels = []
        data.colors = []

        ArrayUtils.range(0, data.numPorts).forEach(function (i) {
            data.portIds[i] = data[`portId${i}`]
            data.labels[i] = data[`portLabel${i}`]
            data.colors[i] = data[`portColor${i}`]
        })

        super.toWidget(data, widget)
    }

    fromPort(port, fieldName) {
        /* We don't want widget label to be updated from any selected port */
        return {
            unit: port.unit
        }
    }

}


/**
 * @alias qtoggle.dashboard.widgets.charts.PieChart
 * @extends qtoggle.dashboard.widgets.charts.BaseChartWidget
 */
class PieChart extends BaseChartWidget {

    static CHART_TYPE = 'pie'

    static displayName = gettext('Pie Chart')
    static typeName = 'PieChart'
    static icon = new StockIcon({name: 'widget-pie-chart', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm


    /**
     * @constructs
     */
    constructor() {
        super()

        /* The widget requires at least one port */
        this._ports = [
            {portId: null, label: '', color: ''}
        ]

        this._unit = ''
        this._multiplier = 100
    }

    isValid() {
        return this._ports.every(function (portInfo) {

            let port = this.getPort(portInfo.portId)
            return Boolean(port && port.enabled && port.online !== false && port.type === 'number')

        }.bind(this))
    }

    configToJSON() {
        return {
            unit: this._unit,
            multiplier: this._multiplier,
            portIds: this._ports.map(p => p.portId),
            labels: this._ports.map(p => p.label),
            colors: this._ports.map(p => p.color)
        }
    }

    configFromJSON(json) {
        if (json.unit != null) {
            this._unit = json.unit
        }
        if (json.multiplier != null) {
            this._multiplier = json.multiplier
        }

        if (json.portIds != null) {
            this._ports = json.portIds.map(function (portId, i) {
                return {
                    portId: portId,
                    label: json.labels != null ? json.labels[i] : '',
                    color: json.colors != null ? json.colors[i] : ''
                }
            })
        }
    }

    showCurrentValue() {
        let data, labels

        if (this._ports.length > 1) {
            data = []
            labels = []
            this._ports.forEach(function (portInfo) {

                let value = this.getPortValue(portInfo.portId)
                data.push(value)
                labels.push(portInfo.label)

            }.bind(this))
        }
        else {
            let portInfo = this._ports[0]
            let portValue = this.getPortValue(portInfo.portId)
            if (portValue == null) {
                return
            }

            let value = portValue * this._multiplier

            data = [value, 100 - value]
            labels = []
        }

        /* Also round values to decent number of decimals */
        data = data.map(d => Math.round(d * 1e6) / 1e6)

        this.widgetCall('setValue', data)
        this.widgetCall({labels: labels})
    }

    onPortValueChange(portId, value) {
        if (!this._ports.some(p => p.portId === portId)) {
            return
        }

        if (!this.getPanel().isActive()) {
            return
        }

        this.showCurrentValue()
    }

    makeChartOptions() {
        let colors = this._ports.map(p => p.color)
        if (this._ports.length === 1) {
            let color = Colors.alpha(Theme.getColor(colors[0]), 0.2)
            colors.push(color)
        }

        return ObjectUtils.combine(super.makeChartOptions(), {
            legend: this._ports.length > 1 ? 'right' : null,
            unitOfMeasurement: this._ports.length > 1 ? this._unit : '%',
            colors: colors
        })
    }

    makePadding() {
        return {
            top: 0.2,
            right: 0,
            bottom: 0.2,
            left: 0
        }
    }

}

Widgets.register(PieChart)


export default PieChart
