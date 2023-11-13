/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 * with the License. A copy of the License is located at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 * OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

import { Container, Header, PieChart, PieChartProps, Select, SelectProps } from "@cloudscape-design/components";
import React, { Component, RefObject } from "react";

export interface PieOrDonutChartProps extends PieChartProps {
    headerDescription: string;
    headerText: string;
    enableSelection: boolean;
    defaultChartMode: "piechart" | "donutchart";
}

interface PieOrDonutChartState {
    chartMode: "piechart" | "donutchart";
}

class PieOrDonutChart extends Component<PieOrDonutChartProps, PieOrDonutChartState> {
    chartSelector: RefObject<SelectProps.Ref>;

    constructor(props: PieOrDonutChartProps) {
        super(props);
        this.chartSelector = React.createRef();
        this.state = {
            chartMode: this.props.defaultChartMode,
        };
    }

    buildHeaderActions() {
        let donutSelectionOption = { label: "Donut", value: "donut" };
        let pieSelectionOption = { label: "Pie", value: "pie" };
        let selectionOption = donutSelectionOption;
        if (this.state.chartMode === "piechart") {
            selectionOption = pieSelectionOption;
        }
        return (
            this.props.enableSelection && (
                <Select
                    ref={this.chartSelector}
                    options={[pieSelectionOption, donutSelectionOption]}
                    selectedOption={selectionOption}
                    onChange={({ detail }) => {
                        let chartMode: "piechart" | "donutchart" = "piechart";
                        if (detail.selectedOption.value === "donut") {
                            chartMode = "donutchart";
                        }
                        this.setState({
                            chartMode: chartMode,
                        });
                    }}
                />
            )
        );
    }

    render() {
        return (
            <Container
                header={
                    <Header actions={this.buildHeaderActions()} variant={"h2"} description={this.props.headerDescription}>
                        {this.props.headerText}
                    </Header>
                }
            >
                <PieChart
                    data={this.props.data}
                    size={this.props.size}
                    variant={this.state.chartMode === "piechart" ? "pie" : "donut"}
                    detailPopoverContent={this.props.detailPopoverContent}
                    detailPopoverSize={this.props.detailPopoverSize}
                    hideLegend={this.props.hideLegend}
                    hideTitles={this.props.hideTitles}
                    hideDescriptions={this.props.hideDescriptions}
                    hideFilter={this.props.hideFilter}
                    innerMetricValue={this.props.innerMetricValue}
                    innerMetricDescription={this.props.innerMetricDescription}
                    legendTitle={this.props.legendTitle}
                    additionalFilters={this.props.additionalFilters}
                    highlightedSegment={this.props.highlightedSegment}
                    visibleSegments={this.props.visibleSegments}
                    statusType={this.props.statusType}
                    empty={this.props.empty}
                    noMatch={this.props.noMatch}
                    loadingText={this.props.loadingText}
                    errorText={this.props.errorText}
                    recoveryText={this.props.recoveryText}
                    onRecoveryClick={this.props.onRecoveryClick}
                    onHighlightChange={this.props.onHighlightChange}
                    onFilterChange={this.props.onFilterChange}
                    ariaLabel={this.props.ariaLabel}
                    ariaLabelledby={this.props.ariaLabelledby}
                    ariaDescription={this.props.ariaDescription}
                    i18nStrings={this.props.i18nStrings}
                />
            </Container>
        );
    }
}

export default PieOrDonutChart;
