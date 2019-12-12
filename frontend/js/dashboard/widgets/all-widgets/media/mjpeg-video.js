import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields.js'
import {TextField}       from '$qui/forms/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'

import * as Widgets     from '$app/dashboard/widgets/widgets.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'


class ConfigForm extends WidgetConfigForm {

    constructor(widget) {
        super(widget, {
            fields: [
                new TextField({
                    name: 'url',
                    label: gettext('URL'),
                    required: true
                }),
                new ColorComboField({
                    name: 'backgroundColor',
                    label: gettext('Background Color'),
                    filterEnabled: true,
                    required: true
                }),
                new CheckField({
                    name: 'preserveAspectRatio',
                    label: gettext('Preserve Aspect Ratio')
                })
            ]
        })
    }

}


export default class MJPEGVideo extends Widget {

    constructor() {
        super()

        this._url = null
        this._backgroundColor = '@background-color'
        this._preserveAspectRatio = true

        this._videoElement = null
    }

    isValid() {
        return Boolean(this._url)
    }

    makeContent(width, height) {
        let spacer = $('<div class="dashboard-mjpeg-video-spacer"></div>')
        spacer.css('background', Theme.getColor(this._backgroundColor))

        let container = $('<div class="dashboard-mjpeg-video-container"></div>')
        spacer.append(container)

        this._videoElement = this._makeVideoElement(width, height)
        container.append(this._videoElement)

        return spacer
    }

    _makeVideoElement(width, height) {
        let videoElement = $(`<img class="dashboard-mjpeg-video-element" src="${this._url}" alt="">`)

        if (!this._preserveAspectRatio) {
            videoElement.css('height', '100%')
        }

        return videoElement
    }

    configToJSON() {
        return {
            url: this._url,
            backgroundColor: this._backgroundColor,
            preserveAspectRatio: this._preserveAspectRatio
        }
    }

    configFromJSON(json) {
        if (json.url != null) {
            this._url = json.url
        }
        if (json.backgroundColor) {
            this._backgroundColor = json.backgroundColor
        }
        if (json.preserveAspectRatio != null) {
            this._preserveAspectRatio = json.preserveAspectRatio
        }
    }

}

// TODO es7 class fields
MJPEGVideo.category = gettext('Media')
MJPEGVideo.displayName = gettext('MJPEG Video')
MJPEGVideo.typeName = 'MJPEGVideo'
MJPEGVideo.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
MJPEGVideo.ConfigForm = ConfigForm
MJPEGVideo.vResizable = true
MJPEGVideo.hResizable = true
MJPEGVideo.hasFrame = true


Widgets.register(MJPEGVideo)