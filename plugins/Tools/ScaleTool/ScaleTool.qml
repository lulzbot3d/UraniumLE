// Copyright (c) 2022 UltiMaker
// Uranium is released under the terms of the LGPLv3 or higher.

import QtQuick 2.15
import QtQuick.Controls 2.2

import UM 1.7 as UM

Item
{
    id: base
    width: childrenRect.width
    height: childrenRect.height
    UM.I18nCatalog { id: catalog; name: "uranium"}

    // We use properties for the text as doing the bindings indirectly doesn't cause any breaks
    // Javascripts don't seem to play well with the bindings (and sometimes break em)
    property string xPercentageText
    property string yPercentageText
    property string zPercentageText

    property string heightText
    property string depthText
    property string widthText

    function getPercentage(scale){
        return scale * 100
    }

    //Rounds a floating point number to 4 decimals. This prevents floating
    //point rounding errors.
    //
    //input:    The number to round.
    //decimals: The number of decimals (digits after the radix) to round to.
    //return:   The rounded number.
    function roundFloat(input, decimals)
    {
        //First convert to fixed-point notation to round the number to 4 decimals and not introduce new floating point errors.
        //Then convert to a string (is implicit). The fixed-point notation will be something like "3.200".
        //Then remove any trailing zeroes and the radix.
        if(input)
        {
            return input.toFixed(decimals).replace(/\.?0*$/, ""); //Match on periods, if any ( \.? ), followed by any number of zeros ( 0* ), then the end of string ( $ ).
        }
        else
        {
            return 0
        }
    }

    function selectTextInTextfield(selected_item)
    {
        selected_item.selectAll()
        selected_item.focus = true
    }

    UM.ToolbarButton
    {
        id: resetScaleButton
        anchors.top: textfields.bottom
        anchors.topMargin: UM.Theme.getSize("default_margin").height
        anchors.left: textfields.left
        anchors.leftMargin: UM.Theme.getSize("default_margin").width
        z: 2

        //: Reset scale tool button
        text: catalog.i18nc("@action:button","Reset")

        toolItem: UM.ColorImage
        {
            source: UM.Theme.getIcon("ArrowReset")
            color: UM.Theme.getColor("icon")
        }

        onClicked: UM.Controller.triggerAction("resetScale")
    }

    UM.ToolbarButton
    {
        id: scaleToMaxButton
        anchors.top: textfields.bottom
        anchors.topMargin: UM.Theme.getSize("default_margin").height
        anchors.left: resetScaleButton.right
        anchors.leftMargin: UM.Theme.getSize("default_margin").width
        z: 1

        //: Scale to max tool button
        text: catalog.i18nc("@action:button", "Scale to Max")

        toolItem: UM.ColorImage
        {
            source: UM.Theme.getIcon("ScaleMax")
            color: UM.Theme.getColor("icon")
        }

        onClicked: UM.Controller.triggerAction("scaleToMax")
    }

    Flow
    {
        id: checkboxes

        anchors.left: scaleToMaxButton.right
        anchors.leftMargin: UM.Theme.getSize("default_margin").width
        anchors.right: parent.right
        anchors.verticalCenter: resetScaleButton.verticalCenter

        UM.CheckBox
        {
            id: snapScalingCheckbox

            width: parent.width //Use a width instead of anchors to allow the flow layout to resolve positioning.
            text: catalog.i18nc("@option:check", "Snap Scaling")

            checked: UM.Controller.properties.getValue("ScaleSnap")
            onClicked:
            {
                UM.Controller.setProperty("ScaleSnap", checked)
                if (snapScalingCheckbox.checked)
                {
                    UM.Controller.setProperty("ScaleX", parseFloat(xPercentage.text) / 100)
                    UM.Controller.setProperty("ScaleY", parseFloat(yPercentage.text) / 100)
                    UM.Controller.setProperty("ScaleZ", parseFloat(zPercentage.text) / 100)
                }
            }
        }

        Binding
        {
            target: snapScalingCheckbox
            property: "checked"
            value: UM.Controller.properties.getValue("ScaleSnap")
        }

        UM.CheckBox
        {
            id: uniformScalingCheckbox

            width: parent.width //Use a width instead of anchors to allow the flow layout to resolve positioning.
            text: catalog.i18nc("@option:check", "Uniform Scaling")

            checked: !UM.Controller.properties.getValue("NonUniformScale")
            onClicked: UM.Controller.setProperty("NonUniformScale", !checked)
            tooltip: catalog.i18nc("@checkbox:description", "If a model has been rotated then 'Non-Uniform Scaling' might result in skewing of the model.")
        }

        Binding
        {
            target: uniformScalingCheckbox
            property: "checked"
            value: !UM.Controller.properties.getValue("NonUniformScale")
        }
    }

    Grid
    {
        id: textfields

        anchors.top: parent.top

        columns: 3
        flow: Grid.TopToBottom
        spacing: Math.round(UM.Theme.getSize("default_margin").width / 2)

        UM.Label
        {
            height: UM.Theme.getSize("setting_control").height
            text: "X"
            color: UM.Theme.getColor("x_axis")
            width: Math.ceil(contentWidth) //Make sure that the grid cells have an integer width.
        }

        UM.Label
        {
            height: UM.Theme.getSize("setting_control").height
            text: "Y"
            color: UM.Theme.getColor("z_axis") // This is intentional. The internal axis are switched.
            width: Math.ceil(contentWidth) //Make sure that the grid cells have an integer width.
        }

        UM.Label
        {
            height: UM.Theme.getSize("setting_control").height
            text: "Z"
            color: UM.Theme.getColor("y_axis") // This is intentional. The internal axis are switched.
            width: Math.ceil(contentWidth) //Make sure that the grid cells have an integer width.
        }
        UM.TextFieldWithUnit
        {
            id: widthTextField
            width: UM.Theme.getSize("setting_control").width
            height: UM.Theme.getSize("setting_control").height
            unit: "mm"

            text: widthText
            validator: UM.FloatValidator
            {
                maxBeforeDecimal: 8
                maxAfterDecimal: 4
            }

            onEditingFinished:
            {
                var modified_text = text.replace(",", ".") // User convenience. We use dots for decimal values
                UM.Controller.setProperty("ObjectWidth", modified_text)
            }
            Keys.onBacktabPressed: selectTextInTextfield(yPercentage)
            Keys.onTabPressed: selectTextInTextfield(xPercentage)
        }

        UM.TextFieldWithUnit
        {
            id: depthTextField
            width: UM.Theme.getSize("setting_control").width
            height: UM.Theme.getSize("setting_control").height
            unit: "mm"
            text: depthText
            validator: UM.FloatValidator
            {
                maxBeforeDecimal: 8
                maxAfterDecimal: 4
            }

            onEditingFinished:
            {
                var modified_text = text.replace(",", ".") // User convenience. We use dots for decimal values
                UM.Controller.setProperty("ObjectDepth", modified_text)
            }
            Keys.onBacktabPressed: selectTextInTextfield(xPercentage)
            Keys.onTabPressed: selectTextInTextfield(zPercentage)
        }
        UM.TextFieldWithUnit
        {
            id: heightTextField
            width: UM.Theme.getSize("setting_control").width
            height: UM.Theme.getSize("setting_control").height
            unit: "mm"

            text: heightText
            validator: UM.FloatValidator
            {
                maxBeforeDecimal: 8
                maxAfterDecimal: 4
            }

            onEditingFinished:
            {
                var modified_text = text.replace(",", ".") // User convenience. We use dots for decimal values
                UM.Controller.setProperty("ObjectHeight", modified_text)
            }
            Keys.onBacktabPressed: selectTextInTextfield(zPercentage)
            Keys.onTabPressed: selectTextInTextfield(yPercentage)
        }

        // To ensure that the new size after scaling matches is still validate (size cannot be less than 0.1 mm).
        // This function checks that by applying the new scale to the original size and checks if the new size is
        // valid. If valid, the new size will be returned, otherwise -1 which means not valid.
        function validateMinimumSize(newValue, lastValue, currentModelSize)
        {
            var modifiedText = newValue.replace(",", ".") // User convenience. We use dots for decimal values
            var parsedNewValue = parseFloat(modifiedText)
            var originalSize = (100 * currentModelSize) / lastValue // model size without scaling
            var newSize = (parsedNewValue * originalSize) / 100
            const minAllowedSize = 0.1 // The new size cannot be lower than this value

            if (newSize >= minAllowedSize)
            {
                return parsedNewValue
            }

            return -1
        }

        function evaluateTextChange(text, lastEnteredValue, valueName, scaleName)
        {
            var currentModelSize = UM.Controller.properties.getValue(valueName)
            var parsedValue = textfields.validateMinimumSize(text, lastEnteredValue, currentModelSize)
            if (parsedValue > 0 && ! UM.Controller.properties.getValue("NonUniformScale"))
            {
                var scale = parsedValue / lastEnteredValue
                var x = UM.Controller.properties.getValue("ScaleX") * 100
                var y = UM.Controller.properties.getValue("ScaleY") * 100
                var z = UM.Controller.properties.getValue("ScaleZ") * 100
                var newX = textfields.validateMinimumSize(
                    (x * scale).toString(), x, UM.Controller.properties.getValue("ObjectWidth"))
                var newY = textfields.validateMinimumSize(
                    (y * scale).toString(), y, UM.Controller.properties.getValue("ObjectHeight"))
                var newZ = textfields.validateMinimumSize(
                    (z * scale).toString(), z, UM.Controller.properties.getValue("ObjectDepth"))
                if (newX <= 0 || newY <= 0 || newZ <= 0)
                {
                    parsedValue = -1
                }
            }
            if (parsedValue > 0)
            {
                UM.Controller.setProperty(scaleName, parsedValue / 100)
                lastEnteredValue = parsedValue
            } // 'else' the value is not valid (the object will become too small)
            return lastEnteredValue
        }

        UM.TextFieldWithUnit
        {
            id: xPercentage
            width: UM.Theme.getSize("setting_control").width
            height: UM.Theme.getSize("setting_control").height
            unit: "%"
            text: xPercentageText
            validator: UM.FloatValidator
            {
                maxBeforeDecimal: 8
                maxAfterDecimal: 4
            }
            property var lastEnteredValue: parseFloat(xPercentageText)
            onEditingFinished:
                lastEnteredValue = textfields.evaluateTextChange(text, lastEnteredValue, "ObjectWidth", "ScaleX")
            Keys.onBacktabPressed: selectTextInTextfield(widthTextField)
            Keys.onTabPressed: selectTextInTextfield(depthTextField)
        }
        UM.TextFieldWithUnit
        {
            id: zPercentage
            width: UM.Theme.getSize("setting_control").width
            height: UM.Theme.getSize("setting_control").height
            unit: "%"
            text: zPercentageText
            validator: UM.FloatValidator
            {
                maxBeforeDecimal: 8
                maxAfterDecimal: 4
            }
            property var lastEnteredValue: parseFloat(yPercentageText)
            onEditingFinished:
                lastEnteredValue = textfields.evaluateTextChange(text, lastEnteredValue, "ObjectHeight", "ScaleZ")
            Keys.onBacktabPressed: selectTextInTextfield(heightTextField)
            Keys.onTabPressed: selectTextInTextfield(widthTextField)
        }
        UM.TextFieldWithUnit
        {
            id: yPercentage
            width: UM.Theme.getSize("setting_control").width
            height: UM.Theme.getSize("setting_control").height
            unit: "%"


            text: yPercentageText
            validator: UM.FloatValidator
            {
                maxBeforeDecimal: 8
                maxAfterDecimal: 4
            }
            property var lastEnteredValue: parseFloat(yPercentageText)
            onEditingFinished:
                lastEnteredValue = textfields.evaluateTextChange(text, lastEnteredValue, "ObjectHeight", "ScaleY")
            Keys.onBacktabPressed: selectTextInTextfield(heightTextField)
            Keys.onTabPressed: selectTextInTextfield(widthTextField)

        }

        // We have to use indirect bindings, as the values can be changed from the outside, which could cause breaks
        // (for instance, a value would be set, but it would be impossible to change it).
        // Doing it indirectly does not break these.
        Binding
        {
            target: base
            property: "heightText"
            value: base.roundFloat(UM.Controller.properties.getValue("ObjectHeight"), 4)
        }

        Binding
        {
            target: base
            property: "widthText"
            value: base.roundFloat(UM.Controller.properties.getValue("ObjectWidth"), 4)
        }

        Binding
        {
            target: base
            property: "depthText"
            value:base.roundFloat(UM.Controller.properties.getValue("ObjectDepth"), 4)
        }

        Binding
        {
            target: base
            property: "xPercentageText"
            value: base.roundFloat(100 * UM.Controller.properties.getValue("ScaleX"), 4)
        }

        Binding
        {
            target: base
            property: "yPercentageText"
            value: base.roundFloat(100 * UM.Controller.properties.getValue("ScaleY"), 4)
        }

        Binding
        {
            target: base
            property: "zPercentageText"
            value: base.roundFloat(100 * UM.Controller.properties.getValue("ScaleZ"), 4)
        }
    }
}
