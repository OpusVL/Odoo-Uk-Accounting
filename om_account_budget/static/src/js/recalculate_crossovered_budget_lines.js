odoo.define('om_account_budget.RecalculateCrossoveredBudgetLines', function (require) {
    "use strict";

    var rpc = require('web.rpc');
    var core = require('web.core');
    var QWeb = core.qweb;
    var ListController = require('web.ListController');
    var PivotController = require('web.PivotController');
    var GraphController = require('web.GraphController');

    var CrossoveredBudgetLinesControllerMixin = {

	_bindRecalculateCrossoveredBudgetLines: function () {
            if (!this.$buttons) {
		return;
            }
            var self = this;
            this.$buttons.on('click', '.o_button_recalculate', function () {
		rpc.query({
		    model: 'crossovered.budget.lines',
		    method: 'recalculate_crossovered_budget_lines',
		}).then(function(ret) {
		    // Re-fetch the data to update the user who clicked the buttons view.
		    // Would use normal actions however access to things like `do_action()` are not
		    // available here, so we just simulate hitting enter in the searchbox
		    var e = $.Event("keydown");
		    e.which = 13; // Enter
		    $(".o_searchview_input").trigger(e);
		});
            });
	}
    };

    ListController.include({
        renderButtons: function () {
            this._super.apply(this, arguments); // Sets this.$buttons
            CrossoveredBudgetLinesControllerMixin._bindRecalculateCrossoveredBudgetLines.call(this);
        }
    });

    PivotController.include({
	// DEBT: Unfortunately the standard PivotController doesn't render the QWEB template
	// with `widget: this` passed in, and instead just passes in an arbitrary local array
	// so we have to override the function to do this so that the
	// qweb can succesfully only display the button _only_ on the model we care about.
	// This has the benefit of making it as simple as (above) the ListController.include()
	// for any future modules that extend PivotController to add more buttons.
	// We still pass in `measures` so that we don't have to amend the original QWeb template.

	// TODO(peter): PR this function override upstream along with the QWEB changes
        renderButtons: function ($node) {
            if ($node) {
		var measures = _.sortBy(
		    _.pairs(_.omit(this.measures, '__count')), function (x) {
			return x[1].string.toLowerCase();
                    }
		)
		this.$buttons = $(QWeb.render('PivotView.buttons', {widget: this, measures: measures}));
		this.$buttons.click(this._onButtonClick.bind(this));
		this.$buttons.find('button').tooltip();
		this.$buttons.appendTo($node);
		this._updateButtons();
            }
	    // END FUNCTION OVERRIDE

	    CrossoveredBudgetLinesControllerMixin._bindRecalculateCrossoveredBudgetLines.call(this);
        }
    });

    GraphController.include({
	// NOTE(peter): The same override as PivotController is required here
	renderButtons: function ($node) {
            if ($node) {
		var measures = _.sortBy(
		    _.pairs(_.omit(this.measures, '__count__')), function (x) {
			return x[1].string.toLowerCase()
		    }
		);
		this.$buttons = $(QWeb.render('GraphView.buttons', {widget: this, measures: measures}));
		this.$measureList = this.$buttons.find('.o_graph_measures_list');
		this.$buttons.find('button').tooltip();
		this.$buttons.click(this._onButtonClick.bind(this));
		this._updateButtons();
		this.$buttons.appendTo($node);
		if (this.isEmbedded) {
                    this._addGroupByMenu($node, this.groupableFields).then(function(){
			var groupByButton = $node.find('.o_dropdown_toggler_btn');
			groupByButton.removeClass("o_dropdown_toggler_btn btn btn-secondary dropdown-toggle");
			groupByButton.addClass("btn dropdown-toggle btn-outline-secondary");
                    });
		}
            }
	    // END FUNCTION OVERRIDE

	    CrossoveredBudgetLinesControllerMixin._bindRecalculateCrossoveredBudgetLines.call(this);

	},
    });
});
