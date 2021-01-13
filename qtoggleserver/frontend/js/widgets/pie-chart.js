
import $ from '$qui/lib/jquery.module.js'

import * as Colors      from '$qui/utils/colors.js'
import * as ObjectUtils from '$qui/utils/object.js'

import * as ChartJS from '$app/lib/chartjs.module.js'

import './base-chart.js'


$.widget('qtoggle.piechart', $.qtoggle.basechart, {
    /* Expected format for value is one of:
     *  * [v0, v1, ...]
     */

    options: {
        showTotal: true
    },

    type: 'doughnut',

    _drawExtra: function (environment, chart, ctx) {
        if (this.options.showTotal) {
            /* Draw the total value in the center of the pie */

            let xCenter = (chart.chartArea.left + chart.chartArea.right) / 2
            let yCenter = (chart.chartArea.top + chart.chartArea.bottom) / 2
            let chartAreaWidth = chart.chartArea.right - chart.chartArea.left
            let chartAreaHeight = chart.chartArea.bottom - chart.chartArea.top
            let minChartAreaDimension = Math.min(chartAreaWidth, chartAreaHeight)
            let fontScaleFactor = minChartAreaDimension / environment.em2px / 20 /* 20 is determined empirically */

            let fontOptions = ObjectUtils.combine(this._makeFontOptions(environment), {
                size: environment.em2px * 2 * fontScaleFactor
            })
            let font = ChartJS.toFont(fontOptions)
            let text = this._makeTotalValueText()

            ctx.save()
            ctx.translate(xCenter, yCenter)
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.font = font.string
            ctx.fillStyle = environment.foregroundColor
            ctx.fillText(text, 0, 0)
            ctx.restore()
        }
    },

    _makeTotalValueText: function () {
        let totalValue = this._data.reduce((a, v) => a + v, 0)
        return `${totalValue}${this.options.unitOfMeasurement || ''}`
    },

    _makeExtraOptions: function (environment) {
        return ObjectUtils.combine(this._super(environment), {
            cutoutPercentage: 66
        })
    },

    _makeTooltipOptions: function (environment) {
        return ObjectUtils.combine(this._super(environment), {
            callbacks: {
                labelColor: function (context) {
                    /* Hack to force fill color to be the same as stroke (border) color */
                    return {
                        borderColor: environment.foregroundColor,
                        backgroundColor: context.element.options.backgroundColor
                    }
                },
                label: function (context) {
                    return ` ${context.dataPoint}${this.options.unitOfMeasurement || ''}`
                }.bind(this)
            }
        })
    },

    _makeLegendOptions: function (environment) {
        let options = this._super(environment)
        let labels = this.options.labels
        let unit = this.options.unitOfMeasurement
        let fontSize = options.labels.font.size

        options.labels.generateLabels = function (chart) {
            if (!labels || labels.length < 2) {
                return []
            }

            let aspectRatio = this.chart.width / this.chart.height
            let dupLabels = aspectRatio < 2

            /* Pie chart extracts all legend labels from the one single data set */
            chart.data.labels = labels
            let generatedLabels = ChartJS.DoughnutController.defaults.plugins.legend.labels.generateLabels(chart)

            /* Calculate values and percents */
            let values = chart.data.datasets[0].data
            let valuesSum = values.reduce((a, v) => a + v, 0)
            let valuesStr = values.map(v => `${v}${unit}`)
            let percents = values.map(v => v * 100 / valuesSum)
            let percentsStr = percents.map(p => `${Math.round(p * 10) / 10}%`)

            /* Show additional details, such as actual value and percent */
            let finalLabels = []

            if (dupLabels) {
                generatedLabels.forEach(function (label, i) {

                    let dupLabel = ObjectUtils.copy(label, /* deep = */ true)
                    dupLabel.pointStyle = 'dash'
                    dupLabel.lineWidth = 0
                    dupLabel.text = `${valuesStr[i]} | ${percentsStr[i]}`

                    finalLabels.push(label)
                    finalLabels.push(dupLabel)

                })

                /* Reduce font size a bit if displaying extra details in duplicated labels */
                this.chart.legend.options.labels.font.size = fontSize * 0.8
            }
            else {
                generatedLabels.forEach(function (label, i) {
                    label.text += ` | ${valuesStr[i]} | ${percentsStr[i]}`
                    finalLabels.push(label)
                })
            }

            return finalLabels
        }

        return options
    },

    _adaptDatasets: function (data, environment, colors) {
        if (!Array.isArray(data) || data.length === 0) {
            return []
        }

        return [{
            backgroundColor: colors,
            hoverBackgroundColor: colors.map(c => Colors.alpha(c, 0.75)),
            borderColor: environment.backgroundColor,
            hoverBorderColor: environment.backgroundColor,
            borderWidth: environment.px2,
            data: data
        }]
    }

})
