
import $ from '$qui/lib/jquery.module.js'

import {gettext} from '$qui/base/i18n.js'

import Widget           from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'


export class BaseChartConfigForm extends WidgetConfigForm {
}


/**
 * @alias qtoggle.dashboard.widgets.charts.BaseChartWidget
 * @extends qtoggle.dashboard.widgets.Widget
 */
export class BaseChartWidget extends Widget {

    static CHART_TYPE = 'override.me'

    static category = gettext('Charts')
    static noProgressInteraction = true
    static vResizable = true
    static hResizable = true
    static hasFrame = true

    /**
     * @constructs
     */
    constructor() {
        super()

        this._chartContainer = null
        this.widgetCall = null
    }

    makeContent(width, height) {
        this._chartContainer = $('<div></div>', {class: 'dashboard-chart-widget-container'})
        this._chartContainer.css({width: `${width}em`, height: `${height}em`})
        this.makeChart(this._chartContainer)

        return this._chartContainer
    }

    makeChart(div) {
        let widget = div[`${this.constructor.CHART_TYPE}chart`]

        this.widgetCall = function (...args) {
            return widget.apply(div, args)
        }

        this.widgetCall(this.makeChartOptions())
    }

    makeChartOptions() {
        let cellWidth = this.getCellWidth()
        let scalingFactor = this.getEmSize() * Widgets.LABEL_FONT_SIZE
        let padding = this.makePadding()

        return {
            scalingFactor: scalingFactor,
            showTooltips: true,
            extraChartOptions: {
                layout: {
                    padding: {
                        top: padding.top * cellWidth,
                        right: padding.right * cellWidth,
                        bottom: padding.bottom * cellWidth,
                        left: padding.left * cellWidth
                    }
                }
            }
        }
    }

    makePadding() {
        return {
            top: 0,
            right: 0,
            bottom: 0,
            left: 0
        }
    }

}
