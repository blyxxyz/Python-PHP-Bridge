<?php
declare(strict_types=1);

namespace PythonBridge;

/**
 * Process commands from another process
 *
 * This class allows another process to communicate with PHP and run PHP code.
 * It receives commands, executes them, and returns the result. The exact
 * method of communication should be defined in inheriting classes, but it's
 * assumed to use JSON or some other format that maps to arrays, strings and
 * numbers.
 *
 * @package PythonBridge
 */
abstract class CommandBridge
{
    /**
     * Receive a command from the other side of the bridge
     *
     * Waits for a command. If one is received, returns it. If the other side
     * is closed, return false.
     *
     * @psalm-suppress MismatchingDocblockReturnType
     * @return array{cmd: string, data: mixed}|false
     */
    abstract protected function receive(): array;

    /**
     * Send a response to the other side of the bridge
     *
     * @param array $data
     *
     * @return void
     */
    abstract protected function send(array $data);

    /**
     * Encode a value into something JSON-serializable
     *
     * @param mixed $data
     *
     * @return array{type: string, value: mixed}
     */
    protected function encode($data): array
    {
        if (is_int($data) || is_string($data) || is_null($data) ||
            is_bool($data)) {
            return [
                'type' => gettype($data),
                'value' => $data
            ];
        } elseif (is_float($data)) {
            if (is_nan($data) || is_infinite($data)) {
                $data = (string)$data;
            }
            return [
                'type' => 'double',
                'value' => $data
            ];
        } elseif (is_array($data)) {
            return [
                'type' => 'array',
                'value' => array_map([$this, 'encode'], $data)
            ];
        } else {
            if (is_object($data)) {
                $cls = get_class($data);
                throw new \Exception("Can't encode object of class '$cls'");
            } else {
                $type = gettype($data);
                throw new \Exception("Can't encode value of type '$type'");
            }
        }
    }

    /**
     * Convert deserialized data into the value it represents, inverts encode
     *
     * @param array{type: string, value: mixed} $data
     *
     * @return mixed
     */
    protected function decode(array $data)
    {
        //['type' => $type, 'value' => $value] = $data;
        $type = $data['type'];
        $value = $data['value'];
        switch ($type) {
            case 'integer':
            case 'string':
            case 'NULL':
            case 'boolean':
                return $value;
            case 'double':
                if ($value === 'NAN') {
                    return NAN;
                } elseif ($value === 'INF') {
                    return INF;
                }
                return $value;
            case 'array':
                return array_map([$this, 'decode'], $value);
            case 'thrownException':
                throw new \Exception($value['message']);
            default:
                throw new \Exception("Unknown type '$type'");
        }
    }

    /**
     * Encode an exception so it can be thrown on the other side
     *
     * @param \Throwable $exception
     *
     * @return array{type: string,
     *               value: array{type: string,
     *                            message: string}}
     */
    private function encodeException(\Throwable $exception)
    {
        return [
            'type' => 'thrownException',
            'value' => [
                'type' => get_class($exception),
                'message' => $exception->getMessage()
            ]
        ];
    }

    /**
     * Continually listen for commands
     *
     * @return void
     */
    public function communicate()
    {
        while (($command = $this->receive()) !== false) {
            $cmd = $command['cmd'];
            $data = $command['data'];
            try {
                $response = $this->encode($this->execute($cmd, $data));
            } catch (\Throwable $exception) {
                $response = $this->encodeException($exception);
            }
            $this->send($response);
        }
    }

    /**
     * Execute a command and return the (unencoded) result
     *
     * @param string $command The name of the command
     * @param mixed  $data    The parameters of the commands
     *
     * @return mixed
     */
    private function execute(string $command, $data)
    {
        switch ($command) {
            case 'getConst':
                return Commands::getConst($data);
            case 'callFun':
                $name = $data['name'];
                $args = $data['args'];
                $args = array_map([$this, 'decode'], $args);
                return Commands::callFun($name, $args);
            case 'listConsts':
                return Commands::listConsts($data);
            case 'listFuns':
                return Commands::listFuns($data);
            default:
                throw new \Exception("Unknown command '$command'");
        }
    }
}
