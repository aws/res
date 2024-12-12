package util

import (
	"strings"
	"testing"
	"github.com/stretchr/testify/assert"
)

func TestConfig(t *testing.T) {

	// Test reading from a file specified in the environment
	t.Setenv("CONFIG_PATH", "../resources/cognito_auth.conf")

	config, err := ParseConfig()
	if err != nil {
		t.Errorf("Couldn't parse: %s", err)
	}

	known_keys := []string{"user_pool_id", "client_id", "aws_region"}

	for _, key := range known_keys {
		if _, exists := config[key]; !exists {
			t.Errorf("Didn't find [%s] in config map.", key)
		}
	}

	key := known_keys[0]
	t.Setenv(strings.ToUpper(key), "override")
	config, _ = ParseConfig()

	if val, exists := config[key]; !exists || val != "override" {
		t.Errorf("Didn't find [%s] in config map or invalid value: %s.", key, val)
	}
}

func TestConvertToBase27WithSimpleRange(t *testing.T) {
    firstTestResult, firstErr := convertToBase27("a", 1, 100)
    assert.Nil(t, firstErr)
    assert.Equal(t, firstTestResult, uint64(1))

    secondTestResult, secondErr := convertToBase27("aa", 1, 100)
    assert.Nil(t, secondErr)
    // 1 * 27 + 1 = 28
    assert.Equal(t, secondTestResult, uint64(28))


    // Test when min id is 10.
    thirdTestResult, thirdErr := convertToBase27("a", 10, 100)
    assert.Nil(t, thirdErr)
    assert.Equal(t, thirdTestResult, uint64(10))    // Expected value is 10 since `a` is first letter


    fourthTestResult, fourthErr := convertToBase27("b", 10, 100)
    assert.Nil(t, fourthErr)
    assert.Equal(t, fourthTestResult, uint64(11))    // Expected value is 11 since `b` is second letter
}

func TestConvertToBase27WithInvalidRange(t *testing.T) {
    testResult, err := convertToBase27("z", 11, 20)
    assert.EqualErrorf(t, err,  "Value id of 36 is larger than max value 20", "Error was not thrown when convert string has id value larger than max value")
    assert.Equal(t, testResult, uint64(0))
}

func TestConvertToBase27WithLargestString(t *testing.T) {
    testResult, err := convertToBase27("zzzzzz", 2000200001, 4294967294)
    assert.Nil(t, err)
    // 'zzzzzz' converted to base 27 decimal
    // 26 * 27^5 + 26 * 27^4 + 26 * 27^3 + 26 * 27^2 + 26 * 27^1 + 26 * 27^0 = 387420488
    // Shift number by 2000200001 - 1 since 2000200001 is minimum value
    // (387420488 - 1) + 2000200001 = 2387620488
    assert.Equal(t, testResult, uint64(2387620488))
}