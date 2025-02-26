#!/usr/bin/env bash

TEST_SCRIPT_PATH=$(dirname "$0")
declare -a TEST_PLAYS
declare -a TEST_RESULTS

# run_one_test_play <playbook name>
run_one_test_play()
{
    if ! ansible-playbook -v $1 -M $TEST_SCRIPT_PATH/../library; then
        TEST_RESULTS=("${TEST_RESULTS[@]}" "FAILED")
    else
        TEST_RESULTS=("${TEST_RESULTS[@]}" "PASSED")
    fi
}

###########################################################

# Install a fresh version of the the module and the plugin
$TEST_SCRIPT_PATH/../install.sh

# Run all tests: they all start with `async_`
for test_play in $TEST_SCRIPT_PATH/async_*.yml
do
    TEST_PLAYS=("${TEST_PLAYS[@]}" "$(basename $test_play)")
    run_one_test_play "$test_play"
done

# Print the report
printf "%-50s|  %s\n" "Test" "Result"

for ((i=0; i < 60; i++))
do
    printf "-"
done
echo ""

for (( i=0; i < ${#TEST_PLAYS[*]}; i++ ))
do
    printf "%-50s|  %s\n" "${TEST_PLAYS[$i]}" "${TEST_RESULTS[$i]}"
done

