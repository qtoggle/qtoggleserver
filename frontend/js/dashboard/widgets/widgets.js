
export {STATE_NORMAL, STATE_PROGRESS, STATE_ERROR} from '$qui/views/view.js'


/* Following constants are expressed as fraction of cell width (em) */
export const CELL_SPACING = 0.05
export const CELL_PADDING = 0.05
export const LABEL_HEIGHT = 0.2
export const BEZEL_WIDTH = 0.025
export const LABEL_FONT_SIZE = 0.13

export const STATE_INVALID = 'invalid'

let registry = []


/**
 * @param {Function} cls
 */
export function register(cls) {
    let categoryInfo = registry.find(function (c) {
        return c.name === cls.getCategory()
    })

    if (!categoryInfo) {
        categoryInfo = {
            name: cls.getCategory(),
            widgetClasses: []
        }
        registry.push(categoryInfo)
    }

    categoryInfo.widgetClasses.push(cls)
}

/**
 * @param {String} type
 * @returns {?Function}
 */
export function find(type) {
    let cls = null
    registry.find(function (categoryInfo) {
        cls = categoryInfo.widgetClasses.find(function (cls) {
            return cls.getType() === type
        })

        if (cls) {
            return true
        }
    })

    return cls
}

/**
 * @returns {Object[]}
 */
export function getRegistry() {
    return registry.slice()
}
